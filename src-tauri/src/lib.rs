#[cfg(not(mobile))]
mod sidecar;

#[cfg(not(mobile))]
use tauri::{Manager, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default();
    #[cfg(not(mobile))]
    let builder = builder.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
        }
    }));
    #[cfg(not(mobile))]
    let builder = builder.invoke_handler(tauri::generate_handler![sidecar::api_config]);

    let app = builder
        .setup(|app| {
            #[cfg(not(mobile))]
            app.manage(sidecar::initialize(app.handle()));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the Vibebook shell");

    app.run(|app_handle, event| {
        #[cfg(not(mobile))]
        if let RunEvent::Exit = event {
            sidecar::stop(app_handle);
        }
    });
}
