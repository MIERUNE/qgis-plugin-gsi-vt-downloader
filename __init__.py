# Plugin entry point


def classFactory(iface):
    from .vtdownloader import VTDownloader

    return VTDownloader(iface)
