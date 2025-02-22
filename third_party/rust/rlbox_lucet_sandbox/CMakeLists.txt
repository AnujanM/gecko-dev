cmake_minimum_required(VERSION 3.11)

project(rlbox_lucet
        VERSION 0.1
        DESCRIPTION "RLBox integration with WASM modules compiled with lucet")

# Project Settings ###################

# set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(WERR "Enable warnings as errors" OFF)

if(MSVC)
  add_compile_options(/W4)
  if(WERR)
    add_compile_options(/WX)
  endif()
else()
  add_compile_options(-Wall -Wextra -pedantic)
  if(WERR)
    add_compile_options(-Werror)
  endif()
endif()

# Dev Tools ###################

find_program(CLANG_TIDY "clang-tidy")
if(CLANG_TIDY)
  # Config in .clang-tidy
  set(CMAKE_CXX_CLANG_TIDY clang-tidy)
endif()

file(GLOB_RECURSE
     ALL_CXX_SOURCE_FILES
     include/*.[chi]pp
     include/*.[chi]xx
     include/*.cc
     include/*.hh
     include/*.ii
     include/*.[CHI]
     test/*.[chi]pp
     test/*.[chi]xx
     test/*.cc
     test/*.hh
     test/*.ii
     test/*.[CHI]
     c_src/*.[chi]pp
     c_src/*.[chi]xx
     c_src/*.cc
     c_src/*.hh
     c_src/*.ii
     c_src/*.[CHI])

find_program(CLANG_FORMAT "clang-format")
if(CLANG_FORMAT)
  # Config in .clang-format
  add_custom_target(format-source
                    COMMAND clang-format
                            -i
                            -style=file
                            ${ALL_CXX_SOURCE_FILES})
endif()

find_program(CARGO "cargo")
if(!CARGO)
  message(
    FATAL_ERROR
      "Could not find cargo. Please install cargo as it is needed to build rust libraries."
    )
endif()

# Dependencies ###################

include(FetchContent)

FetchContent_Declare(
  rlbox
  GIT_REPOSITORY https://github.com/PLSysSec/rlbox_api_cpp17.git)
FetchContent_GetProperties(rlbox)
if(NOT catch2_POLULATED)
  FetchContent_Populate(rlbox)
endif()

FetchContent_Declare(catch2
                     GIT_REPOSITORY https://github.com/catchorg/Catch2.git
                     GIT_TAG v2.9.1)
FetchContent_GetProperties(catch2)
if(NOT catch2_POLULATED)
  FetchContent_Populate(catch2)
endif()

add_subdirectory("${catch2_SOURCE_DIR}")
list(APPEND CMAKE_MODULE_PATH "${catch2_SOURCE_DIR}/contrib")

FetchContent_Declare(
  wasiclang
  URL
    https://github.com/CraneStation/wasi-sdk/releases/download/wasi-sdk-6/wasi-sdk-6.0-linux.tar.gz
  )
FetchContent_GetProperties(wasiclang)
if(NOT wasiclang_POLULATED)
  FetchContent_Populate(wasiclang)
endif()

FetchContent_Declare(
  mod_lucet
  GIT_REPOSITORY https://github.com/PLSysSec/lucet_sandbox_compiler)
FetchContent_GetProperties(mod_lucet)
if(NOT mod_lucet_POLULATED)
  FetchContent_Populate(mod_lucet)
endif()
# Rust Lib ###################

set(LUCET_DIR "${CMAKE_BINARY_DIR}/cargo/release/")
set(LUCET_PATH "${LUCET_DIR}/lucetc")
file(GLOB_RECURSE LUCET_SOURCE_FILES ${mod_lucet_SOURCE_DIR}/*.rs ${mod_lucet_SOURCE_DIR}/*.S)

add_custom_command(OUTPUT ${LUCET_PATH}
                   DEPENDS ${LUCET_SOURCE_FILES}
                           ${mod_lucet_SOURCE_DIR}/Cargo.toml
                   COMMAND CARGO_TARGET_DIR=${CMAKE_BINARY_DIR}/cargo
                           ${CARGO}
                           build
                           --release
                   WORKING_DIRECTORY ${mod_lucet_SOURCE_DIR}
                   COMMENT "Building customized lucet compiler")
add_custom_target(lucet_release ALL DEPENDS ${LUCET_PATH})

# set(mod_lucet_SOURCE_DIR "${CMAKE_SOURCE_DIR}/../lucet_sandbox_compiler")
# set(LUCET_DIR "${mod_lucet_SOURCE_DIR}/target/debug/")
# set(LUCET_PATH "${LUCET_DIR}/lucetc")

file(GLOB_RECURSE RUST_SOURCE_FILES src/*.rs)

# Use the dynamic library as wasi symbols needed by the wasm module are hosted
# in it. If we include the static version, we need to make the main executable
# expose symbols through rdynamic
set(RUST_LIB_DEBUG_PATH
    "${CMAKE_BINARY_DIR}/cargo/debug/librlbox_lucet_sandbox.so")
add_custom_command(OUTPUT ${RUST_LIB_DEBUG_PATH}
                   DEPENDS ${RUST_SOURCE_FILES} ${LUCET_SOURCE_FILES} Cargo.toml
                   COMMAND CARGO_TARGET_DIR=${CMAKE_BINARY_DIR}/cargo ${CARGO}
                           build
                   COMMENT "Building librlbox_lucet_sandbox debug")
add_custom_target(lucet_sandbox_rustlib_debug ALL
                  DEPENDS ${RUST_LIB_DEBUG_PATH})

set(RUST_LIB_RELEASE_PATH
    "${CMAKE_BINARY_DIR}/cargo/release/librlbox_lucet_sandbox.so")
add_custom_command(OUTPUT ${RUST_LIB_RELEASE_PATH}
                   DEPENDS ${RUST_SOURCE_FILES} ${LUCET_SOURCE_FILES} Cargo.toml
                   COMMAND CARGO_TARGET_DIR=${CMAKE_BINARY_DIR}/cargo
                           ${CARGO}
                           build
                           --release
                   COMMENT "Building librlbox_lucet_sandbox release")
add_custom_target(lucet_sandbox_rustlib_release ALL
                  DEPENDS ${RUST_LIB_RELEASE_PATH})

add_library(lucet_sandbox_rustlib SHARED IMPORTED)
set_target_properties(lucet_sandbox_rustlib
                      PROPERTIES IMPORTED_LOCATION ${RUST_LIB_DEBUG_PATH})
set_target_properties(lucet_sandbox_rustlib
                      PROPERTIES IMPORTED_LOCATION_DEBUG ${RUST_LIB_DEBUG_PATH})
set_target_properties(lucet_sandbox_rustlib
                      PROPERTIES IMPORTED_LOCATION_RELEASE
                                 ${RUST_LIB_RELEASE_PATH})

# Tests ###################

include(CTest)
include(Catch)

find_program(WASMCLANG "clang")

if(!WASMCLANG)
  message(
    FATAL_ERROR
      "Require clang with support for target 'wasm32-wasi' to build the WASM module"
    )
endif()

file(GLOB_RECURSE C_SOURCE_FILES c_src/*)
set(GLUE_LIB_WASM "${CMAKE_BINARY_DIR}/wasm/glue_lib_lucet.wasm")
set(GLUE_LIB_SO "${CMAKE_BINARY_DIR}/wasm/glue_lib_lucet.so")

add_custom_command(OUTPUT ${GLUE_LIB_WASM} ${GLUE_LIB_SO}
                   DEPENDS ${C_SOURCE_FILES}
                   WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/c_src
                   COMMAND rlbox_SOURCE_DIR=${rlbox_SOURCE_DIR}
                           wasiclang_SOURCE_DIR=${wasiclang_SOURCE_DIR}
                           LUCET_DIR=${LUCET_DIR}
                           LUCET_WASI_DIR=${mod_lucet_SOURCE_DIR}/lucet-wasi
                           cmake
                           -S
                           .
                           -B
                           ${CMAKE_BINARY_DIR}/wasm
                   COMMAND VERBOSE=1
                           cmake
                           --build
                           ${CMAKE_BINARY_DIR}/wasm
                           --target
                           all
                   COMMENT "Building wasm library")

add_custom_target(glue_lib_wasm ALL DEPENDS ${GLUE_LIB_WASM} ${GLUE_LIB_SO})

add_executable(test_rlbox_glue test/test_lucet_sandbox_glue_main.cpp
                               test/test_lucet_sandbox_glue.cpp
                               test/test_lucet_sandbox_glue_preload.cpp)
target_include_directories(test_rlbox_glue PUBLIC include)
target_include_directories(test_rlbox_glue
                           PUBLIC ${rlbox_SOURCE_DIR}/code/include)
target_include_directories(test_rlbox_glue
                           PUBLIC ${rlbox_SOURCE_DIR}/code/tests/rlbox_glue)
target_include_directories(test_rlbox_glue
                           PUBLIC ${rlbox_SOURCE_DIR}/code/tests/rlbox_glue/lib)

find_package(Threads REQUIRED)

target_compile_definitions(test_rlbox_glue PUBLIC
                           GLUE_LIB_LUCET_PATH="${GLUE_LIB_SO}")

target_link_libraries(test_rlbox_glue
                      Catch2::Catch2
                      lucet_sandbox_rustlib
                      ${CMAKE_THREAD_LIBS_INIT}
                      ${CMAKE_DL_LIBS}
                      # glue_lib_lucet
                      )

if(UNIX)
  target_link_libraries(test_rlbox_glue rt)
endif()
catch_discover_tests(test_rlbox_glue)

