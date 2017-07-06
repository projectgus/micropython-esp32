import badge, machine, gc

if machine.reset_cause() != machine.DEEPSLEEP_RESET:
    badge.init()
    import launcher

gc.collect()
