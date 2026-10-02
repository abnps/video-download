# libvdmp3.so: LAME 3.100 (samo koder, LGPL; izvor sa lame.sourceforge.net, SHA-256
# ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e) + JNI most vdmp3.c.
# CMake umjesto ndk-build-a: ndk-build ne podnosi razmak u putanji („C:\Video Downloader").
cmake_minimum_required(VERSION 3.22)
project(vdmp3 C)

set(LAME ${CMAKE_CURRENT_SOURCE_DIR}/lame/libmp3lame)
add_library(vdmp3 SHARED
    vdmp3.c
    ${LAME}/bitstream.c ${LAME}/encoder.c ${LAME}/fft.c ${LAME}/gain_analysis.c ${LAME}/id3tag.c
    ${LAME}/lame.c ${LAME}/mpglib_interface.c ${LAME}/newmdct.c ${LAME}/presets.c ${LAME}/psymodel.c
    ${LAME}/quantize.c ${LAME}/quantize_pvt.c ${LAME}/reservoir.c ${LAME}/set_get.c ${LAME}/tables.c
    ${LAME}/takehiro.c ${LAME}/util.c ${LAME}/vbrquantize.c ${LAME}/VbrTag.c ${LAME}/version.c)
target_include_directories(vdmp3 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/lame/include ${LAME})
# ieee754_float32_t inače definiše LAME-ov configure (config.h), koji se ovdje ne pokreće.
target_compile_definitions(vdmp3 PRIVATE STDC_HEADERS HAVE_STDINT_H HAVE_LIMITS_H ieee754_float32_t=float)
target_compile_options(vdmp3 PRIVATE -O2 -w)
target_link_libraries(vdmp3 PRIVATE m)
target_link_options(vdmp3 PRIVATE "-Wl,-z,max-page-size=16384")
