# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
{
  'includes': [
    '../../coreconf/config.gypi'
  ],
  'targets': [
    {
      'target_name': 'intel-gcm-s_lib',
      'type': 'static_library',
      'sources': [
        'intel-aes.s',
        'intel-gcm.s',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      'conditions': [
        [ 'cc_is_clang==1', {
          'cflags': [
            '-no-integrated-as',
          ],
          'cflags_mozilla': [
            '-no-integrated-as',
          ],
          'asflags_mozilla': [
            '-no-integrated-as',
          ],
        }],
      ],
    },
    {
      'target_name': 'intel-gcm-wrap_c_lib',
      'type': 'static_library',
      'sources': [
        'intel-gcm-wrap.c',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      'conditions': [
        [ '(OS=="linux" or OS=="android") and target_arch=="x64"', {
          'dependencies': [
            'intel-gcm-s_lib',
          ],
        }],
      ],
      'cflags': [
        '-mssse3',
      ],
      'cflags_mozilla': [
        '-mssse3'
      ],
    },
    {
      # TODO: make this so that all hardware accelerated code is in here.
      'target_name': 'hw-acc-crypto',
      'type': 'static_library',
      'sources': [
        'verified/Hacl_Chacha20_Vec128.c',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      'conditions': [
        [ 'target_arch=="ia32" or target_arch=="x64"', {
          'cflags': [
            '-mssse3'
          ],
          'cflags_mozilla': [
            '-mssse3'
          ],
          # GCC doesn't define this.
          'defines': [
            '__SSSE3__',
          ],
        }],
        [ 'target_arch=="arm"', {
          # Gecko doesn't support non-NEON platform on Android, but tier-3
          # platform such as Linux/arm will need it
          'cflags_mozilla': [
            '-mfpu=neon'
          ],
        }],
      ],
    },
    {
      'target_name': 'gcm-aes-x86_c_lib',
      'type': 'static_library',
      'sources': [
        'gcm-x86.c', 'aes-x86.c'
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      # Enable isa option for pclmul and aes-ni; supported since gcc 4.4.
      # This is only supported by x84/x64. It's not needed for Windows,
      # unless clang-cl is used.
      'cflags_mozilla': [
        '-mpclmul', '-maes'
      ],
      'conditions': [
        [ 'OS=="linux" or OS=="android" or OS=="dragonfly" or OS=="freebsd" or OS=="netbsd" or OS=="openbsd"', {
          'cflags': [
            '-mpclmul', '-maes'
          ],
        }],
        # macOS build doesn't use cflags.
        [ 'OS=="mac" or OS=="ios"', {
          'xcode_settings': {
            'OTHER_CFLAGS': [
              '-mpclmul', '-maes'
            ],
          },
        }]
      ]
    },
    {
      'target_name': 'gcm-aes-aarch64_c_lib',
      'type': 'static_library',
      'sources': [
        'gcm-aarch64.c'
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      'cflags': [
        '-march=armv8-a+crypto'
      ],
      'cflags_mozilla': [
        '-march=armv8-a+crypto'
      ]
    },
    {
      'target_name': 'armv8_c_lib',
      'type': 'static_library',
      'sources': [
        'aes-armv8.c',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ],
      'conditions': [
        [ 'target_arch=="arm"', {
          'cflags': [
            '-march=armv8-a',
            '-mfpu=crypto-neon-fp-armv8'
          ],
          'cflags_mozilla': [
            '-march=armv8-a',
            '-mfpu=crypto-neon-fp-armv8'
          ],
        }, 'target_arch=="arm64" or target_arch=="aarch64"', {
          'cflags': [
            '-march=armv8-a+crypto'
          ],
          'cflags_mozilla': [
            '-march=armv8-a+crypto'
          ],
        }]
      ]
    },
    {
      'target_name': 'freebl',
      'type': 'static_library',
      'sources': [
        'loader.c'
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports'
      ]
    },
    # Build a static freebl library so we can statically link it into
    # the binary. This way we don't have to dlopen() the shared lib
    # but can directly call freebl functions.
    {
      'target_name': 'freebl_static',
      'type': 'static_library',
      'includes': [
        'freebl_base.gypi',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports',
        'hw-acc-crypto',
      ],
      'conditions': [
        [ 'target_arch=="ia32" or target_arch=="x64"', {
          'dependencies': [
            'gcm-aes-x86_c_lib',
          ],
        }, 'disable_arm_hw_aes==0 and (target_arch=="arm" or target_arch=="arm64" or target_arch=="aarch64")', {
          'dependencies': [
            'armv8_c_lib'
          ],
        }],
        [ 'target_arch=="arm64" or target_arch=="aarch64"', {
          'dependencies': [
            'gcm-aes-aarch64_c_lib',
          ],
        }],
        [ 'OS=="linux"', {
          'defines!': [
            'FREEBL_NO_DEPEND',
            'FREEBL_LOWHASH',
            'USE_HW_AES',
            'INTEL_GCM',
          ],
          'conditions': [
            [ 'target_arch=="x64"', {
              # The AES assembler code doesn't work in static builds.
              # The linker complains about non-relocatable code, and I
              # currently don't know how to fix this properly.
              'sources!': [
                'intel-aes.s',
                'intel-gcm.s',
              ],
            }],
          ],
        }],
      ],
    },
    {
      'target_name': '<(freebl_name)',
      'type': 'shared_library',
      'includes': [
        'freebl_base.gypi',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports',
        'hw-acc-crypto',
      ],
      'conditions': [
        [ 'target_arch=="ia32" or target_arch=="x64"', {
          'dependencies': [
            'gcm-aes-x86_c_lib',
          ]
        }, 'target_arch=="arm" or target_arch=="arm64" or target_arch=="aarch64"', {
          'dependencies': [
            'armv8_c_lib',
          ],
        }],
        [ 'target_arch=="arm64" or target_arch=="aarch64"', {
          'dependencies': [
            'gcm-aes-aarch64_c_lib',
          ],
        }],
        [ 'OS!="linux"', {
          'conditions': [
            [ 'moz_fold_libs==0', {
              'dependencies': [
                '<(DEPTH)/lib/util/util.gyp:nssutil3',
              ],
            }, {
              'libraries': [
                '<(moz_folded_library_name)',
              ],
            }],
          ],
        }],
        [ '(OS=="linux" or OS=="android") and target_arch=="x64"', {
          'dependencies': [
            'intel-gcm-wrap_c_lib',
          ],
        }],
        [ 'OS=="win" and cc_is_clang==1', {
          'dependencies': [
            'intel-gcm-wrap_c_lib',
          ],
        }],
        [ 'OS=="linux"', {
          'sources': [
            'nsslowhash.c',
            'stubs.c',
          ],
        }],
      ],
      'variables': {
       'conditions': [
         [ 'OS=="linux"', {
           'mapfile': 'freebl_hash_vector.def',
         }, {
           'mapfile': 'freebl.def',
         }],
       ]
      },
    },
    {
      'target_name': 'freebl_64int_3',
      'includes': [
        'freebl_base.gypi',
      ],
      'type': 'shared_library',
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports',
        'hw-acc-crypto',
      ],
    },
    {
      'target_name': 'freebl_64fpu_3',
      'includes': [
        'freebl_base.gypi',
      ],
      'type': 'shared_library',
      'sources': [
        'mpi/mpi_sparc.c',
        'mpi/mpv_sparcv9.s',
        'mpi/montmulfv9.s',
      ],
      'dependencies': [
        '<(DEPTH)/exports.gyp:nss_exports',
        'hw-acc-crypto',
      ],
      'asflags_mozilla': [
        '-mcpu=v9', '-Wa,-xarch=v9a'
      ],
      'defines': [
        'MP_NO_MP_WORD',
        'MP_USE_UINT_DIGIT',
        'MP_ASSEMBLY_MULTIPLY',
        'MP_USING_MONT_MULF',
        'MP_MONT_USE_MP_MUL',
      ],
    },
  ],
  'conditions': [
    [ 'OS=="linux"', {
      # stub build
      'targets': [
        {
          'target_name': 'freebl3',
          'type': 'shared_library',
          'defines': [
            'FREEBL_NO_DEPEND',
          ],
          'sources': [
            'lowhash_vector.c'
          ],
          'dependencies': [
            '<(DEPTH)/exports.gyp:nss_exports'
          ],
          'variables': {
            'mapfile': 'freebl_hash.def'
          }
        },
      ],
    }],
  ],
  'target_defaults': {
    'include_dirs': [
      'mpi',
      'ecl',
      'verified',
    ],
    'defines': [
      'SHLIB_SUFFIX=\"<(dll_suffix)\"',
      'SHLIB_PREFIX=\"<(dll_prefix)\"',
      'SHLIB_VERSION=\"3\"',
      'SOFTOKEN_SHLIB_VERSION=\"3\"',
      'RIJNDAEL_INCLUDE_TABLES',
      'MP_API_COMPATIBLE'
    ],
    'conditions': [
      [ 'OS=="win" and target_arch=="ia32"', {
        'msvs_settings': {
          'VCCLCompilerTool': {
            #TODO: -Ox optimize flags
            'PreprocessorDefinitions': [
              'MP_ASSEMBLY_MULTIPLY',
              'MP_ASSEMBLY_SQUARE',
              'MP_ASSEMBLY_DIV_2DX1D',
              'MP_USE_UINT_DIGIT',
              'MP_NO_MP_WORD',
              'USE_HW_AES',
              'INTEL_GCM',
            ],
          },
        },
      }],
      [ 'OS=="win" and target_arch=="x64"', {
        'msvs_settings': {
          'VCCLCompilerTool': {
            #TODO: -Ox optimize flags
            'PreprocessorDefinitions': [
              # Should be copied to mingw defines below
              'MP_IS_LITTLE_ENDIAN',
              'NSS_BEVAND_ARCFOUR',
              'MPI_AMD64',
              'MP_ASSEMBLY_MULTIPLY',
              'NSS_USE_COMBA',
              'USE_HW_AES',
              'INTEL_GCM',
            ],
          },
        },
      }],
      [ 'cc_use_gnu_ld==1 and OS=="win" and target_arch=="x64"', {
        # mingw x64
        'defines': [
          'MP_IS_LITTLE_ENDIAN',
         ],
      }],
      [ 'have_int128_support==1', {
        'defines': [
          # The Makefile does version-tests on GCC, but we're not doing that here.
          'HAVE_INT128_SUPPORT',
        ],
      }, {
        'defines': [
          'KRML_NOUINT128',
        ],
      }],
      [ 'OS=="linux"', {
        'defines': [
          'FREEBL_LOWHASH',
          'FREEBL_NO_DEPEND',
        ],
      }],
      [ 'OS=="linux" or OS=="android"', {
        'conditions': [
          [ 'target_arch=="x64"', {
            'defines': [
              'MP_IS_LITTLE_ENDIAN',
              'NSS_BEVAND_ARCFOUR',
              'MPI_AMD64',
              'MP_ASSEMBLY_MULTIPLY',
              'NSS_USE_COMBA',
            ],
          }],
          [ 'target_arch=="x64"', {
            'defines': [
              'USE_HW_AES',
              'INTEL_GCM',
            ],
          }],
          [ 'target_arch=="ia32"', {
            'defines': [
              'MP_IS_LITTLE_ENDIAN',
              'MP_ASSEMBLY_MULTIPLY',
              'MP_ASSEMBLY_SQUARE',
              'MP_ASSEMBLY_DIV_2DX1D',
              'MP_USE_UINT_DIGIT',
            ],
          }],
          [ 'target_arch=="arm"', {
            'defines': [
              'MP_ASSEMBLY_MULTIPLY',
              'MP_ASSEMBLY_SQUARE',
              'MP_USE_UINT_DIGIT',
              'SHA_NO_LONG_LONG',
              'ARMHF',
            ],
          }],
          [ 'disable_arm_hw_aes==0 and (target_arch=="arm" or target_arch=="arm64" or target_arch=="aarch64")', {
            'defines': [
              'USE_HW_AES',
            ],
          }],
        ],
      }],
    ],
  },
  'variables': {
    'module': 'nss',
    'conditions': [
      [ 'OS!="win"', {
        'conditions': [
          [ 'target_arch=="x64" or target_arch=="arm64" or target_arch=="aarch64"', {
            'have_int128_support%': 1,
          }, {
            'have_int128_support%': 0,
          }],
        ],
      }, {
        'have_int128_support%': 0,
      }],
    ],
  }
}
