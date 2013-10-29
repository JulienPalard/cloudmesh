import base64
import hashlib
import sys


def get_fingerprint(entirekey):
        t, keystring, comment = entirekey.split(" ", 2)
        return key_fingerprint(keystring)

def key_fingerprint(key_string):
    key = base64.decodestring(key_string)
    fp_plain = hashlib.md5(key).hexdigest()
    return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))


def key_validate(keytype, filename):
    keystring = "undefined"
    if keytype.lower() == "file":
        try:
            keystring = open(filename, "r").read()
        except:
            return False
    else:
        # TODO: BUG: what is file?
        keystring = file

    try:

        keytype, key_string, comment = keystring.split()
        data = base64.decodestring(key_string)
        int_len = 4
        str_len = struct.unpack('>I', data[:int_len])[
            0]  # this should return 7

        if data[int_len:int_len + str_len] == keytype:
            return True
    except Exception, e:
        print e
        return False
