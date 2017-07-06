import badge, machine, time

if machine.reset_cause() != machine.DEEPSLEEP_RESET:
    badge.init()
    import launcher
