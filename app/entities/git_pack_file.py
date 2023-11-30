from enum import Enum

from app.entities.git_object import ObjectType, GitObject
from app.utils import decompress


class PackObjectType(Enum):
    OBJ_COMMIT = 1
    OBJ_TREE = 2
    OBJ_BLOB = 3
    OBJ_TAG = 4
    OBJ_OFS_DELTA = 6
    OBJ_REF_DELTA = 7

    def object_type(self) -> ObjectType:
        return {
            PackObjectType.OBJ_COMMIT: ObjectType.COMMIT,
            PackObjectType.OBJ_TREE: ObjectType.TREE,
            PackObjectType.OBJ_BLOB: ObjectType.BLOB,
            PackObjectType.OBJ_TAG: ObjectType.TAG,
        }[self]


def unpack_objects(pack_file: bytes):
    git_objects: dict[str, GitObject] = {}

    while pack_file:
        data_start, f_size, f_type = _iterate_pack_file_until_data(pack_file)
        if f_type == PackObjectType.OBJ_REF_DELTA:
            base_sha_1 = pack_file[data_start:data_start + 20].hex()
            data_start += 20
        data, pack_file = decompress(pack_file[data_start:])
        print(f_type, f_size)

        if f_type == PackObjectType.OBJ_REF_DELTA:
            base_object = git_objects[base_sha_1]
            obj_content = _reconstruct_delta(base_object.content, data)
            git_object = GitObject(base_object.object_type, obj_content)
        else:
            git_object = GitObject(f_type.object_type(), data)

        git_objects[git_object.object_id] = git_object

    return git_objects.values()


def _iterate_pack_file_until_data(pack_binary):
    obj_type = None
    obj_size = 0

    for x in range(len(pack_binary)):
        pack_line = pack_binary[x]

        msb = pack_line >> 7
        # If we don't have the type, it means we're on the first row, so we need to get the type
        if not obj_type:
            # First line is [1 byte for MSB][3 bytes for type][4 bytes for size]
            # So we need to get the 3 bytes for type, so we shift 4 to the right and get the last 3 bits
            obj_type = PackObjectType((pack_line >> 4) & 0b0111)
            obj_size += pack_line & 0b0000_1111
        else:
            # If we already have the type, we just need to get the size, so we get the last 7 bits
            obj_size += pack_line & 0b0111_1111

        # this means that the next row has the data
        if msb == 0:
            return x + 1, obj_size, obj_type


def _reconstruct_delta(base, delta) -> bytes:
    source_size, delta = _delta_get_size(delta)
    assert len(base) == source_size

    target_size, delta = _delta_get_size(delta)

    result = bytearray()
    i_delta = 0
    while i_delta < len(delta):
        byte = delta[i_delta]
        msb = byte >> 7

        # The copy instructions contain an offset into the source buffer
        # and the number of bytes to copy from the source to the target buffer starting from that offset.
        if msb == 1:
            offset, size = 0, 0
            offset_shift, size_shift = 0, 0

            # Read variable-length encoded start offset
            for i in range(0, 4):
                # we shift 1 to the left, to get 1, 10, 100, 1000
                if byte & (1 << i) > 0:
                    i_delta += 1
                    offset += delta[i_delta] << offset_shift
                offset_shift += 8

            # Read variable-length encoded size to copy
            for i in range(4, 7):
                if byte & (1 << i) > 0:
                    i_delta += 1
                    size += delta[i_delta] << size_shift
                size_shift += 8

            # There is an exception: size zero is automatically converted to 0x10000
            if size == 0:
                size = 0x10000

            result.extend(base[offset: offset + size])
            i_delta += 1

        # The insert opcode itself is the number of bytes to copy from the delta buffer into the target.
        # This will contain the bytes that have been added and are not part of the source buffer at this point.
        elif msb == 0:
            result.extend(delta[i_delta + 1:i_delta + 1 + byte])
            i_delta += 1 + byte

    assert len(result) == target_size
    return result


def _delta_get_size(delta):
    size = 0
    for b in range(len(delta)):
        # Make the MSB 0 to get the size
        size += (delta[b] & 0b0111_1111) << (7 * b)

        msb = delta[b] >> 7
        if msb == 0:
            # Return size and remaining data
            return size, delta[b + 1:]
