/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * Development of the code in this file was sponsored by Microbric Pty Ltd
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2015 Josef Gajdusek
 * Copyright (c) 2016 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <string.h>

#include "esp_vfs.h"
#include "esp_vfs_fat.h"
#include "esp_system.h"

#include "py/mpconfig.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"
#include "py/mperrno.h"

#include "genhdr/mpversion.h"

extern const mp_obj_type_t mp_fat_vfs_type;

STATIC const qstr os_uname_info_fields[] = {
    MP_QSTR_sysname, MP_QSTR_nodename,
    MP_QSTR_release, MP_QSTR_version, MP_QSTR_machine
};
STATIC const MP_DEFINE_STR_OBJ(os_uname_info_sysname_obj, MICROPY_PY_SYS_PLATFORM);
STATIC const MP_DEFINE_STR_OBJ(os_uname_info_nodename_obj, MICROPY_PY_SYS_PLATFORM);
STATIC const MP_DEFINE_STR_OBJ(os_uname_info_release_obj, MICROPY_VERSION_STRING);
STATIC const MP_DEFINE_STR_OBJ(os_uname_info_version_obj, MICROPY_GIT_TAG " on " MICROPY_BUILD_DATE);
STATIC const MP_DEFINE_STR_OBJ(os_uname_info_machine_obj, MICROPY_HW_BOARD_NAME " with " MICROPY_HW_MCU_NAME);

STATIC MP_DEFINE_ATTRTUPLE(
    os_uname_info_obj,
    os_uname_info_fields,
    5,
    (mp_obj_t)&os_uname_info_sysname_obj,
    (mp_obj_t)&os_uname_info_nodename_obj,
    (mp_obj_t)&os_uname_info_release_obj,
    (mp_obj_t)&os_uname_info_version_obj,
    (mp_obj_t)&os_uname_info_machine_obj
);

STATIC mp_obj_t os_uname(void) {
    return (mp_obj_t)&os_uname_info_obj;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(os_uname_obj, os_uname);

STATIC mp_obj_t os_urandom(mp_obj_t num) {
    mp_int_t n = mp_obj_get_int(num);
    vstr_t vstr;
    vstr_init_len(&vstr, n);
    uint32_t r = 0;
    for (int i = 0; i < n; i++) {
        if ((i & 3) == 0) {
            r = esp_random(); // returns 32-bit hardware random number
        }
        vstr.buf[i] = r;
        r >>= 8;
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(os_urandom_obj, os_urandom);

#if MICROPY_PY_OS_DUPTERM
STATIC mp_obj_t os_dupterm_notify(mp_obj_t obj_in) {
    (void)obj_in;
    mp_hal_signal_dupterm_input();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(os_dupterm_notify_obj, os_dupterm_notify);
#endif

// VFS ESP-IDF

// Handle of the wear levelling library instance
static wl_handle_t s_wl_handle = WL_INVALID_HANDLE;

// allow format partition in case if it is new one and was not formated before
const esp_vfs_fat_mount_config_t mount_config = {
      .max_files = 4,
      .format_if_mount_failed = true
};

mp_obj_t mp_vfs_mount(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    // get the mount point
    size_t len;
    const char *mnt_str = mp_obj_str_get_data(pos_args[1], &len);
    // get the blockdev name
    const char *dev_str = mp_obj_str_get_data(pos_args[0], &len);

    esp_err_t err = esp_vfs_fat_spiflash_mount(mnt_str, dev_str, &mount_config, &s_wl_handle);
    if (err != ESP_OK) {
      mp_raise_OSError(MP_EINVAL);
    }
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_vfs_mount_obj, 2, mp_vfs_mount);


mp_obj_t mp_vfs_umount(mp_obj_t mnt_in) {
    size_t len;
    const char *mnt_str = NULL;
    if (MP_OBJ_IS_STR(mnt_in)) {
        mnt_str = mp_obj_str_get_data(mnt_in, &len);
    } else {
      mp_raise_OSError(MP_EINVAL);
    }

    ESP_ERROR_CHECK(esp_vfs_fat_spiflash_unmount(mnt_str, s_wl_handle));
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(mp_vfs_umount_obj, mp_vfs_umount);

// Exports

STATIC const mp_rom_map_elem_t os_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_uos) },
    { MP_ROM_QSTR(MP_QSTR_uname), MP_ROM_PTR(&os_uname_obj) },
    { MP_ROM_QSTR(MP_QSTR_urandom), MP_ROM_PTR(&os_urandom_obj) },
    #if MICROPY_PY_OS_DUPTERM
    { MP_ROM_QSTR(MP_QSTR_dupterm), MP_ROM_PTR(&mp_uos_dupterm_obj) },
    { MP_ROM_QSTR(MP_QSTR_dupterm_notify), MP_ROM_PTR(&os_dupterm_notify_obj) },
    #endif
    // { MP_ROM_QSTR(MP_QSTR_ilistdir), MP_ROM_PTR(&mp_vfs_ilistdir_obj) },
    // { MP_ROM_QSTR(MP_QSTR_listdir), MP_ROM_PTR(&mp_vfs_listdir_obj) },
    // { MP_ROM_QSTR(MP_QSTR_mkdir), MP_ROM_PTR(&mp_vfs_mkdir_obj) },
    // { MP_ROM_QSTR(MP_QSTR_rmdir), MP_ROM_PTR(&mp_vfs_rmdir_obj) },
    // { MP_ROM_QSTR(MP_QSTR_chdir), MP_ROM_PTR(&mp_vfs_chdir_obj) },
    // { MP_ROM_QSTR(MP_QSTR_getcwd), MP_ROM_PTR(&mp_vfs_getcwd_obj) },
    // { MP_ROM_QSTR(MP_QSTR_remove), MP_ROM_PTR(&mp_vfs_remove_obj) },
    // { MP_ROM_QSTR(MP_QSTR_rename), MP_ROM_PTR(&mp_vfs_rename_obj) },
    // { MP_ROM_QSTR(MP_QSTR_stat), MP_ROM_PTR(&mp_vfs_stat_obj) },
    // { MP_ROM_QSTR(MP_QSTR_statvfs), MP_ROM_PTR(&mp_vfs_statvfs_obj) },
    { MP_ROM_QSTR(MP_QSTR_mount), MP_ROM_PTR(&mp_vfs_mount_obj) },
    { MP_ROM_QSTR(MP_QSTR_umount), MP_ROM_PTR(&mp_vfs_umount_obj) },
    // { MP_ROM_QSTR(MP_QSTR_VfsFat), MP_ROM_PTR(&mp_fat_vfs_type) },
};

STATIC MP_DEFINE_CONST_DICT(os_module_globals, os_module_globals_table);

const mp_obj_module_t uos_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&os_module_globals,
};
