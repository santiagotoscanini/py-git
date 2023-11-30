from zlib import decompressobj


def decompress(content):
    d = decompressobj()
    data = d.decompress(content)

    # unused_data are the remaining bytes that we didn't consume during the decompression
    return data, d.unused_data
