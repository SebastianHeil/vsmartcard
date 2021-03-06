#
# Copyright (C) 2006 Henryk Ploetz
# 
# This file is part of virtualsmartcard.
# 
# virtualsmartcard is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# virtualsmartcard is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
# 
# You should have received a copy of the GNU General Public License along with
# virtualsmartcard.  If not, see <http://www.gnu.org/licenses/>.
#
import string, binascii
from ConstantDefinitions import MAX_SHORT_LE, MAX_EXTENDED_LE

def stringtoint(str): 
    #i = len(str) - 1
    #int = 0
    #while i >= 0:
        #int = (int << i*8) + ord(str[i])
        #i = i - 1
    #return int
    if str:
        return int(str.encode('hex'), 16)
    return 0


def inttostring(i, length=None): 
    #str = ""
    #while i > 0:
        #str = chr(i & 0xff) + str
        #i >>= 8
    str = "%x" % i
    if len(str) % 2 == 0:
        str = str.decode('hex')
    else:
        str = ("0"+str).decode('hex')

    if length:
        l = len(str)
        if l > length:
            raise ValueError("i too big for the specified stringlength")
        else:
            str = chr(0)*(length-l) + str

    return str


_myprintable = " " + string.letters + string.digits + string.punctuation
def hexdump(data, indent = 0, short = False, linelen = 16, offset = 0):
    """Generates a nice hexdump of data and returns it. Consecutive lines will 
    be indented with indent spaces. When short is true, will instead generate 
    hexdump without adresses and on one line.
    
    Examples: 
    hexdump('\x00\x41') -> \
    '0000:  00 41                                             .A              '
    hexdump('\x00\x41', short=True) -> '00 41 (.A)'"""
    
    def hexable(data):
        return " ".join([binascii.b2a_hex(a) for a in data])
    
    def printable(data):
        return "".join([e in _myprintable and e or "." for e in data])
    
    if short:
        return "%s (%s)" % (hexable(data), printable(data))
    
    FORMATSTRING = "%04x:  %-"+ str(linelen*3) +"s  %-"+ str(linelen) +"s"
    result = ""
    (head, tail) = (data[:linelen], data[linelen:])
    pos = 0
    while len(head) > 0:
        if pos > 0:
            result = result + "\n%s" % (' ' * indent)
        result = result + FORMATSTRING % (pos+offset, hexable(head), printable(head))
        pos = pos + len(head)
        (head, tail) = (tail[:linelen], tail[linelen:])
    return result

LIFE_CYCLES = {0x01: "Load file = loaded",
    0x03: "Applet instance / security domain = Installed",
    0x07: "Card manager = Initialized; Applet instance / security domain = Selectable",
    0x0F: "Card manager = Secured; Applet instance / security domain = Personalized",
    0x7F: "Card manager = Locked; Applet instance / security domain = Blocked",
    0xFF: "Applet instance = Locked"}

def parse_status(data):
    """Parses the Response APDU of a GetStatus command."""
    def parse_segment(segment):
        def parse_privileges(privileges):
            if privileges == 0x0:
                return "N/A"
            else:
                privs = []
                if privileges & (1<<7):
                    privs.append("security domain")
                if privileges & (1<<6):
                    privs.append("DAP DES verification")
                if privileges & (1<<5):
                    privs.append("delegated management")
                if privileges & (1<<4):
                    privs.append("card locking")
                if privileges & (1<<3):
                    privs.append("card termination")
                if privileges & (1<<2):
                    privs.append("default selected")
                if privileges & (1<<1):
                    privs.append("global PIN modification")
                if privileges & (1<<0):
                    privs.append("mandated DAP verification")
                return ", ".join(privs)
        
        lgth = ord(segment[0])
        aid = segment[1:1+lgth]
        lifecycle = ord(segment[1+lgth])
        privileges = ord(segment[1+lgth+1])
        
        print("aid length:       %i (%x)" % (lgth, lgth))
        print("aid:              %s" % hexdump(aid, indent = 18, short=True))
        print("life cycle state: %x (%s)" % (lifecycle, LIFE_CYCLES.get(lifecycle, "unknown or invalid state")))
        print("privileges:       %x (%s)\n" % (privileges, parse_privileges(privileges)))

    pos = 0
    while pos < len(data):
        lgth = ord(data[pos])+3
        segment = data[pos:pos+lgth]
        parse_segment(segment)
        pos = pos + lgth

def _unformat_hexdump(dump):
    hexdump = " ".join([line[7:54] for line in dump.splitlines()])
    return binascii.a2b_hex("".join([e != " " and e or "" for e in hexdump]))

def _make_byte_property(prop):
    "Make a byte property(). This is meta code."
    return property(lambda self: getattr(self, "_"+prop, None),
            lambda self, value: self._setbyte(prop, value), 
            lambda self: delattr(self, "_"+prop),
            "The %s attribute of the APDU" % prop)

class APDU(object):
    "Base class for an APDU"
    
    def __init__(self, *args, **kwargs):
        """Creates a new APDU instance. Can be given positional parameters which 
        must be sequences of either strings (or strings themselves) or integers
        specifying byte values that will be concatenated in order. Alternatively
        you may give exactly one positional argument that is an APDU instance.
        After all the positional arguments have been concatenated they must
        form a valid APDU!
        
        The keyword arguments can then be used to override those values.
        Keywords recognized are: 

            - C_APDU: cla, ins, p1, p2, lc, le, data
            - R_APDU: sw, sw1, sw2, data
        """
        
        initbuff = list()
        
        if len(args) == 1 and isinstance(args[0], self.__class__):
            self.parse( args[0].render() )
        else:
            for arg in args:
                if type(arg) == str:
                    initbuff.extend(arg)
                elif hasattr(arg, "__iter__"):
                    for elem in arg:
                        if hasattr(elem, "__iter__"):
                            initbuff.extend(elem)
                        else:
                            initbuff.append(elem)
                else:
                    initbuff.append(arg)
            
            for (index, value) in enumerate(initbuff):
                t = type(value)
                if t == str:
                    initbuff[index] = ord(value)
                elif t != int:
                    raise TypeError("APDU must consist of ints or one-byte strings, not %s (index %s)" % (t, index))
            
            self.parse( initbuff )
        
        for (name, value) in kwargs.items():
            if value is not None:
                setattr(self, name, value)
    
    def _getdata(self):
        return self._data
    def _setdata(self, value): 
        if isinstance(value, str):
            self._data = "".join([e for e in value])
        elif isinstance(value, list):
            self._data = "".join([chr(int(e)) for e in value])
        else:
            raise ValueError("'data' attribute can only be a str or a list of int, not %s" % type(value))
        self.Lc = len(value)
    def _deldata(self):
        del self._data; self.data = ""
    
    data = property(_getdata, _setdata, None,
        "The data contents of this APDU")
    
    def _setbyte(self, name, value):
        #print "setbyte(%r, %r)" % (name, value)
        if isinstance(value, int):
            setattr(self, "_"+name, value)
        elif isinstance(value, str):
            setattr(self, "_"+name, ord(value))
        else:
            raise ValueError("'%s' attribute can only be a byte, that is: int or str, not %s" % (name, type(value)))

    def _format_parts(self, fields):
        "utility function to be used in __str__ and __repr__"
        
        parts = []
        for i in fields:
            parts.append( "%s=0x%02X" % (i, getattr(self, i)) )
        
        return parts
    
    def __str__(self):
        result = "%s(%s)" % (self.__class__.__name__, ", ".join(self._format_fields()))
        
        if len(self.data) > 0:
            result = result + " with %i (0x%02x) bytes of data" % (
                len(self.data), len(self.data) 
            )
            return result + ":\n" + hexdump(self.data)
        else:
            return result
    
    def __repr__(self):
        parts = self._format_fields()
        
        if len(self.data) > 0:
            parts.append("data=%r" % self.data)
        
        return "%s(%s)" % (self.__class__.__name__, ", ".join(parts))

class C_APDU(APDU):
    "Class for a command APDU"
    
    def parse(self, apdu):
        "Parse a full command APDU and assign the values to our object, overwriting whatever there was."
        apdu = map( lambda a: (isinstance(a, str) and (ord(a),) or (a,))[0], apdu)
        apdu = apdu + [0] * max(4-len(apdu), 0)
        
        self.CLA, self.INS, self.P1, self.P2 = apdu[:4] # case 1, 2, 3, 4
        self.__extended_length = False
        if len(apdu) == 4:                              # case 1
            self.data = ""
        elif (len(apdu) >= 7) and (apdu[4] == 0):       # extended length apdu
            self.__extended_length = True
            if len(apdu) == 7:                          # case 2 extended length
                self.Le = (apdu[-2]<<8) + apdu[-1]
                self.data = ""
            else:                                       # case 3, 4 extended length 
                self.Lc = (apdu[5]<<8) + apdu[6]
                if len(apdu) == 7 + self.Lc:            # case 3 extended length
                    self.data = apdu[7:]
                elif len(apdu) == 7 + self.Lc + 3:      # case 4 extended length
                    self.Le = (apdu[-2]<<8) + apdu[-1]
                    self.data = apdu[7:-3]
                elif len(apdu) == 7 + self.Lc + 2 and apdu[-2:] == [0, 0]: # case 4 extended length with max le
                    self.Le = 0
                    self.data = apdu[7:-2]
                else:
                    raise ValueError("Invalid Lc value. Is %s, should be %s or %s"
                            % ( self.Lc, 7 + self.Lc, 7 + self.Lc + 3))
        else:                                           # short apdu
            if len(apdu) == 5:                          # case 2 short apdu
                self.Le = apdu[-1]
                self.data = ""
            elif len(apdu) > 5:                         # case 3, 4 short apdu
                self.Lc = apdu[4]
                if len(apdu) == 5 + self.Lc:            # case 3
                    self.data = apdu[5:]
                elif len(apdu) == 5 + self.Lc + 1:      # case 4
                    self.data = apdu[5:-1]
                    self.Le = apdu[-1]
                else:
                    raise ValueError("Invalid Lc value. Is %s, should be %s or %s" % (self.Lc,
                        5 + self.Lc, 5 + self.Lc + 1))
    
    CLA = _make_byte_property("CLA"); cla = CLA
    INS = _make_byte_property("INS"); ins = INS
    P1 = _make_byte_property("P1");   p1 = P1
    P2 = _make_byte_property("P2");   p2 = P2
    Lc = _make_byte_property("Lc");   lc = Lc
    Le = _make_byte_property("Le");   le = Le
    
    @property
    def effective_Le(self):
        if hasattr(self, "_Le") and (self.Le == 0):
            if self.__extended_length:
                return MAX_EXTENDED_LE 
            else:
                return MAX_SHORT_LE
        else:
            return self.Le

    def _format_fields(self):
        fields = ["CLA", "INS", "P1", "P2"]
        if self.Lc > 0:
            fields.append("Lc")
        if hasattr(self, "_Le"): ## There's a difference between "Le = 0" and "no Le"
            fields.append("Le")
        
        return self._format_parts(fields)
    
    def render(self):
        "Return this APDU as a binary string"
        buffer = []
        
        for i in self.CLA, self.INS, self.P1, self.P2:
            buffer.append(chr(i))
        
        if len(self.data) > 0:
            buffer.append(chr(self.Lc))
            buffer.append(self.data)
        
        if hasattr(self, "_Le"):
            if self.__extended_length:
                buffer.append(chr(0x00))
                buffer.append(chr(self.Le>>8))
                buffer.append(chr(self.Le - self.Le>>8))
            else:
                buffer.append(chr(self.Le))
        
        return "".join(buffer)
    
    def case(self):
        "Return 1, 2, 3 or 4, depending on which ISO case we represent."
        if self.Lc == 0:
            if not hasattr(self, "_Le"):
                return 1
            else:
                return 2
        else:
            if not hasattr(self, "_Le"):
                return 3
            else:
                return 4

    
class R_APDU(APDU):
    "Class for a response APDU"
    
    def _getsw(self):        return chr(self.SW1) + chr(self.SW2)
    def _setsw(self, value):
        if len(value) != 2:
            raise ValueError("SW must be exactly two bytes")
        self.SW1 = value[0]
        self.SW2 = value[1]
    
    SW = property(_getsw, _setsw, None,
        "The Status Word of this response APDU")
    sw = SW
    
    SW1 = _make_byte_property("SW1"); sw1 = SW1
    SW2 = _make_byte_property("SW2"); sw2 = SW2
    
    def parse(self, apdu):
        "Parse a full response APDU and assign the values to our object, overwriting whatever there was."
        self.SW = apdu[-2:]
        self.data = apdu[:-2]
    
    def _format_fields(self):
        fields = ["SW1", "SW2"]
        return self._format_parts(fields)
    
    def render(self):
        "Return this APDU as a binary string"
        return self.data + self.sw
    
if __name__ == "__main__":
    a = C_APDU(1, 2, 3, 4) # case 1
    b = C_APDU(1, 2, 3, 4, 5) # case 2
    c = C_APDU((1, 2, 3), cla = 0x23, data = "hallo") # case 3
    d = C_APDU(1, 2, 3, 4, 2, 4, 6, 0) # case 4
    
    print()
    print(a)
    print(b)
    print(c)
    print(d)
    print()
    print(repr(a))
    print(repr(b))
    print(repr(c))
    print(repr(d))
    
    print()
    for i in a, b, c, d:
        print(hexdump(i.render()))
    
    print()
    e = R_APDU(0x90, 0)
    f = R_APDU("foo\x67\x00")

    print()
    print(e)
    print(f)
    print()
    print(repr(e))
    print(repr(f))

    print()
    for i in e, f:
        print(hexdump(i.render()))

    g = C_APDU(0x00, 0xb0, 0x9c, 0x00, 0x00, 0x00, 0x00) #case 2 extended length
    
    print()
    print(g)
    print(repr(g))
    print(hexdump(g.render()))

    h = C_APDU('\x0c\x2a\x00\xbe\x00\x01\x5f\x87\x82\x01\x51\x01\xf0\xa2\x21\xa1\x36\x27\xb1\x30\x31\x3e\xd0\x97\x09\xb5\xde\x73\x5e\x29\x90\xce\xf1\x3d\x8a\xfd\xe7\x92\xe5\xa4\x70\xb9\x5d\x31\xe2\x34\xe7\xe2\x06\x13\x17\x7a\x3e\xca\x06\x39\x24\x2e\x75\x8c\x29\x6d\xd8\xa3\x1b\x1a\x68\x58\xd0\x1a\x98\xd4\xd8\x19\x50\xe9\x1b\x3c\xd1\xfd\x10\x53\x5b\xf2\x3b\xff\x4a\xf6\x05\xd0\x72\xad\xae\xaa\x93\x1a\x0a\x90\xc8\xa1\xb1\xf1\x0a\xba\x5b\xd2\x23\x38\xf8\x9a\x38\x9e\xa2\x04\x8b\xcb\x8b\x8b\xc0\x80\xd9\x2a\x04\x47\x26\x83\xda\xfe\x57\x68\x6b\x00\xb9\xa2\xea\x96\xf2\x07\x7f\xc5\x9c\xee\xbe\xf3\x81\xbf\x24\x19\x1e\x49\x1e\x9a\x85\x8f\x34\xcb\x1a\x23\xae\x6d\x7f\xa4\xb6\x7b\x60\x5d\x56\x79\x1c\xec\x18\xcc\x09\xdb\xb2\xbb\xf4\x31\xee\x08\x54\x26\xd5\xde\x99\xfa\x43\xa2\x49\x8e\x60\xc0\xaa\x4f\xfd\xf7\xe5\xc8\x89\x43\x5e\x11\xa2\x28\xc4\x92\x11\xda\xba\xe4\x91\xec\x04\xc9\x2c\xbd\x91\x6a\x5e\x7e\xb9\x85\xa2\xfa\x07\xc9\x47\x24\xa4\x3b\x63\xef\x75\x65\xef\xaf\xac\x22\x75\x99\x8b\x19\xde\x95\x76\xc9\xc8\xbc\x30\x23\x48\x07\x28\x19\x1e\x49\x9e\xcb\x99\xc3\x48\xdd\x1d\x0f\x44\x62\x64\x2a\x19\x7b\xeb\xee\xdf\xa1\xa6\xae\x87\x6d\x93\x36\x2d\x35\x8f\xd9\x61\x73\xef\x2d\x39\xb5\xc5\xe2\x75\x4b\x63\x0b\x41\x94\x8c\xbb\x55\xf6\x98\x5f\x9c\x07\xca\xe3\x15\xe4\xe6\x93\xd0\xa3\x9b\x22\xfa\x62\x18\xc5\x63\xfa\x2d\x57\xbb\x29\x2d\x57\x10\xd3\x0c\x05\x80\x15\x27\x4b\xc0\x84\x23\x62\x22\x6b\xae\x39\xa2\x8f\x55\xac\x8e\x08\x34\x46\xcc\x83\xf9\x9d\x2a\x75\x00\x00')
    print()
    print(h)
    print(repr(h))
