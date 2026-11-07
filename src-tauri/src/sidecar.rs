use std::{
    env,
    fs::{self, OpenOptions},
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{mpsc, Mutex},
    thread,
    time::{Duration, Instant},
};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApiConfig {
    pub base_url: String,
    pub token: String,
}

#[derive(Deserialize)]
struct ReadyMessage {
    event: String,
    port: u16,
    token: String,
}

pub struct SidecarState {
    config: Option<ApiConfig>,
    error: Option<String>,
    child: Mutex<Option<Child>>,
}

impl Drop for SidecarState {
    fn drop(&mut self) {
        if let Ok(child) = self.child.get_mut() {
            if let Some(mut child) = child.take() {
                kill_tree(&mut child);
            }
        }
    }
}

pub fn initialize(app: &AppHandle) -> SidecarState {
    let log_path = log_path(app);
    match start(app, &log_path) {
        Ok((config, child)) => SidecarState {
            config: Some(config),
            error: None,
            child: Mutex::new(Some(child)),
        },
        Err(error) => SidecarState {
            config: None,
            error: Some(format!("{error}\nLog: {}", log_path.display())),
            child: Mutex::new(None),
        },
    }
}

#[tauri::command]
pub fn api_config(state: tauri::State<'_, SidecarState>) -> Result<ApiConfig, String> {
    match &state.config {
        Some(config) => Ok(config.clone()),
        None => Err(state
            .error
            .clone()
            .unwrap_or_else(|| "El motor local no está disponible.".to_string())),
    }
}

pub fn stop(app: &AppHandle) {
    if let Some(state) = app.try_state::<SidecarState>() {
        if let Ok(mut child) = state.child.lock() {
            if let Some(mut child) = child.take() {
                kill_tree(&mut child);
            }
        }
    }
}

fn start(app: &AppHandle, log_path: &PathBuf) -> Result<(ApiConfig, Child), String> {
    let token = generate_token()?;
    let mut command = sidecar_command(app)?;
    command
        .args([
            "serve",
            "--json-ready",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--token",
            &token,
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if cfg!(debug_assertions) {
        command.arg("--dev");
    }
    if let Some(library) = portable_library() {
        command.arg("--library").arg(library);
    }

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }

    let mut child = command
        .spawn()
        .map_err(|error| format!("No se pudo iniciar el sidecar: {error}"))?;

    if let Some(stderr) = child.stderr.take() {
        let log_path = log_path.clone();
        thread::spawn(move || write_log(stderr, &log_path));
    }

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "El sidecar no expuso stdout.".to_string())?;
    let (sender, receiver) = mpsc::channel::<String>();
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().map_while(Result::ok) {
            if line.trim_start().starts_with('{') {
                let _ = sender.send(line);
                break;
            }
        }
    });

    let deadline = Instant::now() + Duration::from_secs(30);
    let line = loop {
        match receiver.recv_timeout(Duration::from_millis(200)) {
            Ok(line) => break line,
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(terminate(
                    child,
                    "El sidecar cerró stdout antes de estar listo.",
                ));
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if let Ok(Some(status)) = child.try_wait() {
                    return Err(format!("El sidecar terminó antes de estar listo: {status}"));
                }
                if Instant::now() >= deadline {
                    return Err(terminate(
                        child,
                        "El sidecar tardó más de 30 segundos en iniciar.",
                    ));
                }
            }
        }
    };

    let ready: ReadyMessage = match serde_json::from_str(&line) {
        Ok(ready) => ready,
        Err(error) => {
            return Err(terminate(
                child,
                &format!("Respuesta inválida del sidecar: {error}"),
            ))
        }
    };
    if ready.event != "ready" || ready.token != token {
        return Err(terminate(
            child,
            "El sidecar devolvió un estado de inicio inválido.",
        ));
    }

    Ok((
        ApiConfig {
            base_url: format!("http://127.0.0.1:{}", ready.port),
            token,
        },
        child,
    ))
}

fn sidecar_command(app: &AppHandle) -> Result<Command, String> {
    if let Some(binary) = configured_binary(app) {
        return Ok(Command::new(binary));
    }
    if cfg!(debug_assertions) {
        let mut command = Command::new("uv");
        command
            .args(["run", "vibebook-sidecar"])
            .current_dir(repo_root());
        return Ok(command);
    }
    Err("No se encontró vibebook-sidecar junto a la aplicación.".to_string())
}

fn configured_binary(app: &AppHandle) -> Option<PathBuf> {
    if let Ok(value) = env::var("VIBEBOOK_SIDECAR") {
        let path = PathBuf::from(value);
        if path.is_file() {
            return Some(path);
        }
    }
    if let Ok(resources) = app.path().resource_dir() {
        let path = resources.join("sidecar").join(sidecar_name());
        if path.is_file() {
            return Some(path);
        }
    }
    let dev = repo_root().join("dist").join(sidecar_name());
    dev.is_file().then_some(dev)
}

fn sidecar_name() -> &'static str {
    if cfg!(windows) {
        "vibebook-sidecar.exe"
    } else {
        "vibebook-sidecar"
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .canonicalize()
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".."))
}

fn portable_library() -> Option<PathBuf> {
    let executable = env::current_exe().ok()?;
    let directory = executable.parent()?;
    directory
        .join("portable.flag")
        .is_file()
        .then(|| directory.join("data").join("library"))
}

fn generate_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| format!("No se pudo generar el token local: {error}"))?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn log_path(app: &AppHandle) -> PathBuf {
    let directory = app
        .path()
        .app_log_dir()
        .unwrap_or_else(|_| env::temp_dir().join("vibebook"));
    let _ = fs::create_dir_all(&directory);
    directory.join("vibebook-sidecar.log")
}

fn write_log(stderr: impl std::io::Read, path: &PathBuf) {
    let mut file = OpenOptions::new().create(true).append(true).open(path).ok();
    let reader = BufReader::new(stderr);
    for line in reader.lines().map_while(Result::ok) {
        if let Some(file) = file.as_mut() {
            let _ = writeln!(file, "{line}");
        }
    }
}

fn terminate(mut child: Child, message: &str) -> String {
    kill_tree(&mut child);
    message.to_string()
}

fn kill_tree(child: &mut Child) {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let _ = Command::new("taskkill")
            .args(["/PID", &child.id().to_string(), "/T", "/F"])
            .creation_flags(0x08000000)
            .status();
    }
    let _ = child.kill();
    let _ = child.wait();
}
