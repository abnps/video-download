/*
 * Most između Kotlina (Mp3.kt) i LAME kodera: PCM 16-bit (isprepleteni kanali) → MP3.
 * LAME je pod LGPL-om i gradi se kao zasebna dijeljena biblioteka (libvdmp3.so), vidi cpp/lame/COPYING.
 */
#include <jni.h>
#include <stdint.h>
#include "lame.h"

#define FN(name) Java_io_github_abnps_videodownload_Mp3_##name

JNIEXPORT jlong JNICALL FN(nativeInit)(JNIEnv *env, jclass cls, jint sample_rate, jint channels, jint kbps) {
    lame_global_flags *lame = lame_init();
    if (!lame) return 0;
    lame_set_in_samplerate(lame, sample_rate);
    lame_set_num_channels(lame, channels);
    lame_set_mode(lame, channels == 1 ? MONO : JOINT_STEREO);
    lame_set_brate(lame, kbps);  /* CBR, isto kao na računaru (192 kbps) */
    lame_set_quality(lame, 2);   /* dobar kvalitet, i dalje brzo na telefonu */
    if (lame_init_params(lame) < 0) {
        lame_close(lame);
        return 0;
    }
    return (jlong) (intptr_t) lame;
}

JNIEXPORT jint JNICALL FN(nativeEncode)(JNIEnv *env, jclass cls, jlong handle, jshortArray pcm, jint frames,
                                        jbyteArray out) {
    lame_global_flags *lame = (lame_global_flags *) (intptr_t) handle;
    jshort *samples = (*env)->GetShortArrayElements(env, pcm, NULL);
    jbyte *buffer = (*env)->GetByteArrayElements(env, out, NULL);
    jsize size = (*env)->GetArrayLength(env, out);
    int written = lame_get_num_channels(lame) == 1
        ? lame_encode_buffer(lame, samples, samples, frames, (unsigned char *) buffer, size)
        : lame_encode_buffer_interleaved(lame, samples, frames, (unsigned char *) buffer, size);
    (*env)->ReleaseShortArrayElements(env, pcm, samples, JNI_ABORT);
    (*env)->ReleaseByteArrayElements(env, out, buffer, 0);
    return written;
}

JNIEXPORT jint JNICALL FN(nativeFlush)(JNIEnv *env, jclass cls, jlong handle, jbyteArray out) {
    lame_global_flags *lame = (lame_global_flags *) (intptr_t) handle;
    jbyte *buffer = (*env)->GetByteArrayElements(env, out, NULL);
    jsize size = (*env)->GetArrayLength(env, out);
    int written = lame_encode_flush(lame, (unsigned char *) buffer, size);
    (*env)->ReleaseByteArrayElements(env, out, buffer, 0);
    return written;
}

JNIEXPORT void JNICALL FN(nativeClose)(JNIEnv *env, jclass cls, jlong handle) {
    if (handle) lame_close((lame_global_flags *) (intptr_t) handle);
}
