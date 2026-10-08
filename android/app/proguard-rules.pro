# Klase koje Python (Chaquopy) poziva preko imena: R8 ih ne smije preimenovati ni izbaciti.
# vd_net.py: jclass("io.github.abnps.videodownload.NativeHttp").open(...) i NativeResponse.read/close/status/...
-keep class io.github.abnps.videodownload.NativeHttp { *; }
-keep class io.github.abnps.videodownload.NativeResponse { *; }
# vd_core.download(): listener.onProgress(...) i listener.isCancelled()
-keep class io.github.abnps.videodownload.DownloadService$Listener { *; }
