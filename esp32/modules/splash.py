import ugfx, time, ntp, badge, machine, deepsleep, network, esp, gc
import appglue, services

# File: splash.py
# Version: 3
# Description: Homescreen for SHA2017 badge
# License: MIT
# Authors: Renze Nicolai <renze@rnplus.nl>
#          Thomas Roos   <?>


### FUNCTIONS

# Graphics
def splash_draw_battery(status=""):
    vBatt = badge.battery_volt_sense()
    vBatt += vDrop

    ugfx.clear(ugfx.WHITE)

    width = round((vBatt-vMin) / (vMax-vMin) * 38)
    if width < 0:
        width = 0
    elif width > 38:
        width = 38

    ugfx.box(2,2,40,18,ugfx.BLACK)
    ugfx.box(42,7,2,8,ugfx.BLACK)
    ugfx.area(3,3,width,16,ugfx.BLACK)

    if vBatt > 500:
        if badge.battery_charge_status() and badge.usb_volt_sense() > 4000:
            bat_status = 'Charging...'
        else:
            bat_status = str(round(vBatt/1000, 2)) + 'v'
    else:
        bat_status = 'No battery'
        
    if status!="":
        bat_status = status

    ugfx.string(47, 2, bat_status,'Roboto_Regular18',ugfx.BLACK)

def splash_draw_nickname():
    global nick
    ugfx.string(0, 40, nick, "PermanentMarker36", ugfx.BLACK)

def splash_draw_actions():
    global otaAvailable
    if splash_power_countdown_get()<1: # Badge is going to sleep
        info = '[ ANY: Wake up ]'
    elif otaAvailable: # OTA update available
        info = '[ SELECT: UPDATE ] [ START: LAUNCHER ]'
    else: # Normal operation
        info = '[ START: LAUNCHER ]'

    l = ugfx.get_string_width(info,"Roboto_Regular12")
    ugfx.string(296-l, 0, info, "Roboto_Regular12",ugfx.BLACK)

def splash_draw():
    global splashDrawMsgLineNumber
    splashDrawMsgLineNumber = 0
    ugfx.clear(ugfx.WHITE)
    
    status = ""
    if otaAvailable:
        status = "Update available!"
    
    splash_draw_battery(status)
    splash_draw_nickname()
    splash_draw_actions()
    services.draw()
    ugfx.flush(ugfx.LUT_FULL)
    

def splash_draw_msg(message, clear=False):
    global splashDrawMsgLineNumber
    try:
        splashDrawMsgLineNumber
    except:
        splashDrawMsgLineNumber = 0
        
    if clear:
        ugfx.clear(ugfx.WHITE)
        ugfx.string(0, 0, message, "PermanentMarker22", ugfx.BLACK)
        ugfx.set_lut(ugfx.LUT_FASTER)
        ugfx.flush()
        splashDrawMsgLineNumber = 0
    else:
        ugfx.string(0, 30 + (splashDrawMsgLineNumber * 15), message, "Roboto_Regular12", ugfx.BLACK)
        ugfx.flush()
        splashDrawMsgLineNumber += 1

# WiFi
def splash_wifi_connect():
    global wifiStatus
    try:
        wifiStatus
    except:
        wifiStatus = False
       
    if not wifiStatus:
        nw = network.WLAN(network.STA_IF)
        if not nw.isconnected():
            nw.active(True)
            ssid = badge.nvs_get_str('badge', 'wifi.ssid', 'SHA2017-insecure')
            password = badge.nvs_get_str('badge', 'wifi.password')
            nw.connect(ssid, password) if password else nw.connect(ssid)

            splash_draw_msg("Connecting to WiFi...", True)
            splash_draw_msg("("+ssid+")")

            timeout = badge.nvs_get_u8('splash', 'wifi.timeout', 40)
            while not nw.isconnected():
                time.sleep(0.1)
                timeout = timeout - 1
                if (timeout<1):
                    splash_draw_msg("Timeout while connecting!")
                    splash_wifi_disable()
                    return False
        wifiStatus = True
        return True
    return False

def splash_wifi_active():
    global wifiStatus
    try:
        wifiStatus
    except:
        wifiStatus = False
    return wifiStatus
        
    
def splash_wifi_disable():
    global wifiStatus
    wifiStatus = False
    nw = network.WLAN(network.STA_IF)
    nw.active(False)
    
# NTP clock configuration
def splash_ntp():
    if not splash_wifi_active():
        if not splash_wifi_connect():
            return False
    splash_draw_msg("Configuring clock...", True)
    ntp.set_NTP_time()
    splash_draw_msg("Done")
    return True
    
# OTA update checking

def splash_ota_download_info():
    import urequests as requests
    splash_draw_msg("Checking for updates...", True)
    result = False
    try:
        data = requests.get("https://badge.sha2017.org/version")
    except:
        splash_draw_msg("Error:")
        splash_draw_msg("Could not download JSON!")
        time.sleep(5)
        return False
    try:
        result = data.json()
    except:
        data.close()
        splash_draw_msg("Error:")
        splash_draw_msg("Could not decode JSON!")
        time.sleep(5)
        return False
    data.close()
    return result

def splash_ota_check():
    if not splash_wifi_active():
        if not splash_wifi_connect():
            return False
        
    info = splash_ota_download_info()
    if info:
        import version
        if info["build"] > version.build:
            badge.nvs_set_u8('badge','OTA.ready',1)
            return True

    badge.nvs_set_u8('badge','OTA.ready',0)
    return False

def splash_ota_start():
    pass

# About

def splash_about_countdown_reset():
    global splashAboutCountdown
    splashAboutCountdown = badge.nvs_get_u8('splash', 'about.amount', 10)
    
def splash_about_countdown_trigger():
    global splashAboutCountdown
    try:
        splashAboutCountdown
    except:
        splash_about_countdown_reset()

    splashAboutCountdown -= 1
    if splashAboutCountdown<0:
        appglue.start_app('magic', False)
    else:
        print("[SPLASH] Magic in "+str(splashAboutCountdown)+"...")
            

# Power management

def splash_power_countdown_reset():
    global splashPowerCountdown
    splashPowerCountdown = badge.nvs_get_u8('splash', 'timer.amount', 50)

def splash_power_countdown_get():
    global splashPowerCountdown
    try:
        splashPowerCountdown
    except:
        splash_power_countdown_reset()
    return splashPowerCountdown
  
def splash_power_countdown_trigger():
    global splashPowerCountdown
    try:
        splashPowerCountdown
    except:
        splash_power_countdown_reset()
    
    splashPowerCountdown -= 1
    
    if splashPowerCountdown<1:
        if badge.usb_volt_sense() > 4500:
            print("[SPLASH] USB connected, not sleeping.")
            splash_power_countdown_reset()
    elif splashPowerCountdown<0:
        print("[SPLASH] Going to sleep...")
        badge.eink_busy_wait()
        appglue.start_bpp()
    else:
        print("[SPLASH] Sleep in "+str(splashPowerCountdown)+"...")


# Button input

def splash_input_start(pressed):
    # Pressing start always starts the launcher
    if pressed:
        print("[SPLASH] Start button pressed")
        appglue.start_app("launcher", False)

def splash_input_a(pressed):
    if pressed:
        print("[SPLASH] A button pressed")
        splash_power_countdown_reset()
        splash_about_countdown_trigger()

def splash_input_select(pressed):
    if pressed:
        print("[SPLASH] Select button pressed")
        global otaAvailable
        if otaAvailable:
            splash_ota_start()
        splash_power_countdown_reset()

def splash_input_other(pressed):
    if pressed:
        print("[SPLASH] Other button pressed")
        splash_power_countdown_reset()

def splash_input_init():
    print("[SPLASH] Inputs attached")
    ugfx.input_init()
    ugfx.input_attach(ugfx.BTN_START, splash_input_start)
    ugfx.input_attach(ugfx.BTN_A, splash_input_a)
    ugfx.input_attach(ugfx.BTN_B, splash_input_other)
    ugfx.input_attach(ugfx.BTN_SELECT, splash_input_select)
    ugfx.input_attach(ugfx.JOY_UP, splash_input_other)
    ugfx.input_attach(ugfx.JOY_DOWN, splash_input_other)
    ugfx.input_attach(ugfx.JOY_LEFT, splash_input_other)
    ugfx.input_attach(ugfx.JOY_RIGHT, splash_input_other)

# Event timer
def splash_timer_init():
    global splashTimer
    try:
        splashTimer
        print("[SPLASH] Timer exists already")
    except:
        splashTimer = machine.Timer(-1)
        splashTimer.init(period=badge.nvs_get_u16('splash', 'timer.period', 250), mode=machine.Timer.ONE_SHOT, callback=splash_timer_callback)
        print("[SPLASH] Timer created")
    
def splash_timer_callback(tmr):
    try:
        services.loop(splash_power_countdown_get())
    except:
        pass
    splash_draw()
    splash_power_countdown_trigger()
    tmr.init(period=badge.nvs_get_u16('splash', 'timer.period', 250), mode=machine.Timer.ONE_SHOT, callback=splash_timer_callback)
    
    
### PROGRAM

# Load settings from NVS
nick = badge.nvs_get_str("owner", "name", 'Jan de Boer')
vMin = badge.nvs_get_u16('splash', 'bat.volt.min', 3600) # mV
vMax = badge.nvs_get_u16('splash', 'bat.volt.max', 4200) # mV

# Calibrate battery voltage drop
if badge.battery_charge_status() == False and badge.usb_volt_sense() > 4500 and badge.battery_volt_sense() > 2500:
    badge.nvs_set_u16('splash', 'bat.volt.drop', 5200 - badge.battery_volt_sense()) # mV
    print('Set vDrop to: ' + str(4200 - badge.battery_volt_sense()))
vDrop = badge.nvs_get_u16('splash', 'bat.volt.drop', 1000) - 1000 # mV

# Initialize user input subsystem
splash_input_init()

# Initialize power management subsystem
splash_power_countdown_reset()

# Initialize about subsystem
splash_about_countdown_reset()
    
# Setup / Sponsors / OTA check / NTP clock sync
setupState = badge.nvs_get_u8('badge', 'setup.state', 0)
if setupState == 0: #First boot
    print("[SPLASH] First boot...")
    appglue.start_app("setup")
elif setupState == 1: # Second boot: Show sponsors
    print("[SPLASH] Second boot...")
    badge.nvs_set_u8('badge', 'setup.state', 2)
    appglue.start_app("sponsors")
elif setupState == 2: # Third boot: force OTA check
    print("[SPLASH] Third boot...")
    badge.nvs_set_u8('badge', 'setup.state', 3)
    otaCheck = splash_ntp() if time.time() < 1482192000 else True
    otaAvailable = splash_ota_check()
else: # Normal boot
    print("[SPLASH] Normal boot...")
    otaCheck = splash_ntp() if time.time() < 1482192000 else True
    if (machine.reset_cause() != machine.DEEPSLEEP_RESET) and otaCheck:
        otaAvailable = splash_ota_check()
    else:
        otaAvailable = badge.nvs_get_u8('badge','OTA.ready',0)
    
# Disable WiFi if active
splash_wifi_disable()

# Initialize services
services.setup()

# Initialize timer
#splash_timer_init()

# Clean memory
gc.collect()

# Draw homescreen
splash_draw()
