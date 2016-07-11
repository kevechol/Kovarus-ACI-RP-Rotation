import pexpect
import re
import os

from .nxcli import NXCLI
from cisco.vrf import VRF, set_global_vrf, get_global_vrf


class Transfer(object):

    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10):
        self.expect_list = [\
            "(?i)re you sure you want to continue connecting", \
            "(?i)here is already a file existing with this name. do you want to overwrite", \
            pexpect.TIMEOUT, \
            pexpect.EOF, \
            "(?i)Copy to .* is not permitted", \
            "(?i)No route to host", \
            "(?i)Cmd exec error"
        ]
        self.setup(source, dest, host, vrf, login_timeout)

    @staticmethod
    def gettransferobj (protocol = "", host = "" ,
        source = "", dest = "bootflash:",
        vrf = "management", login_timeout = 10,
        user = "", password = ""):
        if protocol == 'http':
            return HTTPTransfer(source, dest, host, vrf, login_timeout)
        elif protocol == 'tftp':
            return TFTPTransfer(source, dest, host, vrf, login_timeout)
        elif protocol == 'scp':
            return SCPTransfer(source, dest, host, vrf, login_timeout, user, password)
        elif protocol == 'sftp':
            return SFTPTransfer(source, dest, host, vrf, login_timeout, user, password)
        elif protocol == 'ftp':
            return FTPTransfer(source, dest, host, vrf, login_timeout, user, password)
        else:
            raise pexpect.ExceptionPexpect("Protocol not supported")

    def setup(self, source, dest, host, vrf, login_timeout):
        #Host is a tuple in the form (tohost, fromhost)
        self.sethost(host)
        self.setsource(source)
        self.setdest(dest)
        self.setvrf(vrf)
        self.settimeout(login_timeout)
        self.b_len = len(self.expect_list)
        self.getswitchname()

    def gethost(self):
        return self.host

    def sethost(self, host):
        self.host = host
        if self.host[1] == None:
            self.tohost = self.host[1]
        else:
            self.tohost = self.host[1].strip()
            if not self.tohost:
                self.tohost = None
        if self.host[0] == None:
            self.fromhost = self.host[0]
        else:
            self.fromhost = self.host[0].strip()
            if not self.fromhost:
                self.fromhost = None

    def getsource(self):
        return self.source

    def setsource(self, source):
        self.source = source.strip()
        split_src = self.source.split("/")
        self.fname = split_src[-1]

    def getdest(self):
        return self.dest

    def setdest(self, dest):
        self.dest = dest.strip()

    def getvrf(self):
        return self.vrf

    def setvrf(self, vrf):
        self.vrf = vrf.strip()

    def gettimeout(self):
        return self.login_timeout

    def settimeout(self, login_timeout):
        if type(login_timeout) == str:
            try:
                login_timeout = int(login_timeout.strip())
            except ValueError:
                raise pexpect.ExceptionPexpect('Invalid value for login_timeout')
        self.login_timeout = login_timeout

    def protosetup(self):
        raise pexpect.ExceptionPexpect('Inherited class protosetup is empty')

    def _getbaselistlen(self):
        return self.b_len

    def getswitchname(self):
        self.switchname = NXCLI('show switchname', False).get_raw_output().strip()

    def local_file_exist (self, filename=""):
        return os.path.isfile(self.find_local_filename (filename))

    def find_local_filename (self, filename=""):
        if re.match(r'^bootflash:/*.+', filename):
            ret = re.sub (r'^bootflash:*/*', r'/bootflash/', filename)
        elif re.match(r'^bootflash:/*', filename):
            ret = "/bootflash/" + self.fname
        elif re.match(r'^debug:/*', filename):
            ret = re.sub (r'^debug:/*', r'/debug/', filename)
        elif re.match(r'^core:*/*', filename):
            v = map(eval, re.compile (r'\s*core:*/*(\d+)/(\d+)s*', re.I).match(filename).groups())
            v[0] += 100
            globpat = '/var/sysmgr/logs/*_0x%d_*.%d.tar.gz' % tuple(v)
            ret = ''.join(glob.glob(globpat))
        elif re.match(r'^log:/*', filename):
            ret = re.sub (r'^log:/*', r'/log/', filename)
        elif re.match(r'^volatile:/*', filename):
            ret = re.sub (r'^volatile:/*', r'/volatile/', filename)
        elif re.match(r'^volatile:*', filename):
            ret = re.sub (r'^volatile:*', r'/volatile/' + self.fname, filename)
        else:
            ret = "/bootflash/" + filename
        return ret

    def geturi(self):
        prestr  = "/isan/bin/vsh -c 'copy "
        poststr = " vrf %s'" % self.vrf
        if self.istohostdir == False:
            str = self.protocol + "://" + self.fromhost + \
                  "/" + self.source + " " + self.dest
        else:
            str = self.source + " " + self.protocol + "://" \
                  + self.tohost + "/" + self.dest
        return prestr + str + poststr

    def inputvalidation(self):
        if not self.source:
            raise pexpect.ExceptionPexpect("Invalid source file name")

        if not self.dest:
            self.dest = "bootflash:" + self.fname

        if self.login_timeout <= 0:
            raise pexpect.ExceptionPexpect("Invalid value for login_timeout")

        if not self.tohost or self.tohost == None:
            if not self.fromhost or self.fromhost is None:
                raise pexpect.ExceptionPexpect("Invalid host")

        if not self.fromhost or self.fromhost == None:
            if not self.tohost or self.tohost is None:
                raise pexpect.ExceptionPexpect("Invalid host")

        match = None

        if self.tohost is None or self.tohost == self.switchname:
            match = [re.match('\d+\.\d+\.\d+\.\d+', self.fromhost)]
            self.istohostdir = False

        elif self.fromhost is None or self.fromhost == self.switchname:
            match = [re.match('\d+\.\d+\.\d+\.\d+', self.tohost)]
            if not self.local_file_exist(self.source):
                raise pexpect.ExceptionPexpect("%s source file not found" % self.source)
            self.istohostdir = True

        if match is None:
            raise pexpect.ExceptionPexpect("Invalid host")


    def baseprocessresponse(self, i):
        if i==0:
            self.cmd.sendline("yes")
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)
            return i

        elif i==1:
            self.cmd.sendline("yes")
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)
            return i

        elif i==2:
            raise pexpect.ExceptionPexpect("Your request timed out")
            return None

        elif i==3:
            raise pexpect.ExceptionPexpect("Could not complete your request")
            return None

        elif i==4:
            raise pexpect.ExceptionPexpect("Copy to destination " + self.dest + " is not permitted")
            return None

        elif i==5:
            raise pexpect.ExceptionPexpect("No route to host")
            return None

        elif i==6:
            raise pexpect.ExceptionPexpect("Invalid URI path. Please check vrf")
            return None

    def protoprocessresponse(self, i):
        raise pexpect.ExceptionPexpect('Inherited class protoprocessresponse is empty')

    def processresponse(self, i):
        if i<self.b_len:
            return self.baseprocessresponse(i)
        else:
            return self.protoprocessresponse(i)

    def run(self):
        self.status = False
        self.inputvalidation()
        self.uri = self.geturi()
        self.cmd = pexpect.spawn(self.uri)
        i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)
        while i != None:
            i = self.processresponse(i)
        self.cmd.close()

    def postvalidation(self):
        if not self.istohostdir:
            if self.local_file_exist (self.dest):
                print "File in destination " + self.dest
                print "Transfer Complete"
                self.status = True

            else:
                raise pexpect.ExceptionPexpect("File not found in destination. Transfer could not be completed")


    def transferstatus(self):
        if self.fromhost is not None and self.fromhost != switchname:
            file_exist = self.local_file_exist()
            return (file_exist and self.status)
        else:
            return self.status

    def getstatus(self):
        return self.status

class PasswordProtoTransfer (Transfer):

    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10, user = "", password = ""):
        self.setusercredentials(user, password)
        super(PasswordProtoTransfer, self).__init__(source, dest, host, vrf, login_timeout)
        self.expect_list += [\
           "(?i)(?:assword[: ]*)|(?:passphrase for key)", \
           "(?i)(?:permission denied)|(?:login incorrect)"
        ]
        self.p_len = len(self.expect_list)

    def _getbaselistlen(self):
        return self.p_len

    def setusercredentials(self, user, password):
        self.user = user
        self.password = password

    def baseprocessresponse(self, i):
        if i<self.b_len:
            return super(PasswordProtoTransfer, self).baseprocessresponse(i)

        elif i==self.b_len:
            self.cmd.sendline(self.password)
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)

        elif i==self.b_len+1:
            raise pexpect.ExceptionPexpect("Permission Denied")
            i = None

        return i

    def protoprocessresponse(self, i):
         pass

    def processresponse(self, i):
        if i<self.p_len:
            return self.baseprocessresponse(i)
        else:
            return self.protoprocessresponse(i)

    def inputvalidation(self):
        super(PasswordProtoTransfer, self).inputvalidation()
        if not self.user:
            raise pexpect.ExceptionPexpect("Please enter valid username")
        if not self.password:
            raise pexpect.ExceptionPexpect("Please enter valid password")

    def geturi(self):
        prestr  = "/isan/bin/vsh -c 'copy "
        poststr = " vrf %s'" % self.vrf
        if self.istohostdir == False:
            str = self.protocol + "://" + self.user + "@" + self.fromhost + \
                  "/" + self.source + " " + self.dest
        else:
            str = self.source + " " + self.protocol + "://" \
                  + self.user + "@" + self.tohost + "/" + self.dest
        return prestr + str + poststr

class HTTPTransfer (Transfer):
    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10):
        super(HTTPTransfer, self).__init__(source, dest, host, vrf, login_timeout)
        self.protosetup()


    def protosetup(self):
        self.l = self._getbaselistlen()
        self.protocol = 'http'

    def inputvalidation(self):
        super(HTTPTransfer, self).inputvalidation()
        if self.istohostdir:
            raise pexpect.ExceptionPexpect("HTTP transfer from switch is not supported")

    def protoprocessresponse(self, i):
        if i==self.l:
            self.postvalidation()
            i = None
        elif i==self.l+1:
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)
        elif i==self.l+2:
            raise pexpect.ExceptionPexpect("Could not connect to host")
            i = None

        return i


    def run(self):
        import urllib2
        if type(self.vrf) is str:
            vrf = VRF.get_vrf_id_by_name(self.vrf)
        if get_global_vrf() != vrf:
            set_global_vrf(self.vrf)
        
        dest_file = open(self.find_local_filename(self.dest), 'w')
        
        url_fd = urllib2.urlopen('http://%s/%s' % (self.fromhost, self.source),
                timeout = self.login_timeout)
        while True:
            block = url_fd.read(1024)
            dest_file.write(block)
            if len(block) < 1024:
                break;

        dest_file.close()
        url_fd.close()



class TFTPTransfer (Transfer):
    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10):
        super(TFTPTransfer, self).__init__(source, dest, host, vrf, login_timeout)
        self.expect_list += [\
            "TFTP get operation failed:File not found", \
            "[#.*]", \
            "TFTP get operation was successful", \
            "TFTP get operation failed:Connection timed out", \
            "TFTP put operation was successful"
        ]
        self.protosetup()

    def protosetup(self):
        self.l = self._getbaselistlen()
        self.protocol = 'tftp'

    def protoprocessresponse(self, i):
        if i==self.l:
            raise pexpect.ExceptionPexpect("Source file not found. Please check path and file name")
            i = None

        elif i==self.l+1:
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)

        elif i==self.l+2:
            self.postvalidation()
            i = None

        elif i==self.l+3:
            raise pexpect.ExceptionPexpect("Could not connect to host. Connection timed out")
            i = None

        elif i==self.l+4:
            print "Transfer to " + self.dest + " on " + self.tohost + " complete"
            self.status = True
            i = None

        return i

class SCPTransfer (PasswordProtoTransfer):
    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10, user = "", password = ""):
        super(SCPTransfer, self).__init__(source, dest, host, vrf, login_timeout, user, password)
        self.expect_list += [\
            self.fname+".*100%", \
            "(?i)o such file or directory", \
            "(?i)onnection timed out", \
            "(?i)ermission denied", \
            "(?i)cannot access file\s+(\w+)", \
            "(?i)scp:\s+\w+\s+Permission denied", \
            "(?i)Host key verification failed" \
        ]
        self.protosetup()

    def protosetup(self):
        self.l = self._getbaselistlen()
        self.protocol = 'scp'

    def protoprocessresponse(self, i):
        if i==self.l:
            if not self.istohostdir:
                self.postvalidation()
                i = None
            else:
                print "Transfer to " + self.dest + " on " + self.tohost + " complete"
                i = None
                self.status = True


        elif i==self.l+1:
            raise pexpect.ExceptionPexpect("Source file not found")
            i = None

        elif i==self.l+2:
            raise pexpect.ExceptionPexpect("Connection timed out. Check host name")
            i = None

        elif i==self.l+3:
            raise pexpect.ExceptionPexpect("Permission denied for this operation")
            i = None

        elif i==self.l+4:
            raise pexpect.ExceptionPexpect("Cannot access file " +self.cmd.match.group(1))
            i = None

        elif i==self.l+5:
            raise pexpect.ExceptionPexpect("Permission denied ")
            i = None

        elif i==self.l+6:
            raise pexpect.ExceptionPexpect("Host key verification failed")
            i = None

        return i

class FTPTransfer (PasswordProtoTransfer):
    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10, user = "", password = ""):
        super(FTPTransfer, self).__init__(source, dest, host, vrf, login_timeout, user, password)
        self.expect_list += [\
            "Transfer of file Completed Successfully", \
            "Transfer of file aborted, file not found or Login failed", \
            "Transfer of file aborted, server not connected", \
            "copy: cannot access file (\w+)", \
            "host nor service provided, or not known"
        ]
        self.protosetup()

    def protosetup(self):
        self.l = self._getbaselistlen()
        self.protocol = 'ftp'

    def protoprocessresponse(self, i):
        if i==self.l:
            i = self.cmd.expect(self.expect_list, timeout=self.login_timeout)
            if i==3:
                if not self.istohostdir:
                    self.postvalidation()
                    i = None

                else:
                    print "Transfer to " + self.dest + " on " + self.tohost + " complete"
                    i = None
                    self.status = True

            else:
                pass

        elif i==self.l+1:
            raise pexpect.ExceptionPexpect("Source file not found")
            i = None

        elif i==self.l+2:
            raise pexpect.ExceptionPexpect("Server not connected")
            i = None

        elif i==self.l+3:
            raise pexpect.ExceptionPexpect("Cannot access file " + self.cmd.match.group(1))
            i = None

        elif i==self.l+4:
            raise pexpect.ExceptionPexpect("Check host name")
            i = None

        return i

class SFTPTransfer (PasswordProtoTransfer):
    def __init__(self, source, dest = "", host = (None, None), vrf = "management", login_timeout = 10, user = "", password = ""):
        super(SFTPTransfer, self).__init__(source, dest, host, vrf, login_timeout, user, password)
        self.expect_list += [\
            "Couldn't stat remote file: No such file or directory", \
            "\w+\s+100%", \
            "Host key verification failed" \
        ]
        self.protosetup()

    def protosetup(self):
        self.l = self._getbaselistlen()
        self.protocol = 'sftp'

    def protoprocessresponse(self, i):
        if i==self.l:
            raise pexpect.ExceptionPexpect("Source file not found")

        elif i==self.l+1:
            if not self.istohostdir:
                self.postvalidation()
                i = None

            else:
                print "Transfer to " + self.dest + " on " + self.tohost + " complete"
                i = None
                self.status = True
        
        elif i==self.l+2:
            raise pexpect.ExceptionPexpect("Host key verification failed")
            i = None

        return i

def transfer (protocol = "", host = "" ,
        source = "", dest = "bootflash:",
        vrf = "management", login_timeout = 10,
        user = "", password = ""):

    if type(host) != tuple:
        host = (host, None)

    ob = Transfer.gettransferobj(protocol.lower().strip(), host, source, dest, vrf, login_timeout, user, password)
    ob.run()
    return ob


