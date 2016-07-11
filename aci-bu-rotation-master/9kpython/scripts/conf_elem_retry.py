import os, re, sys, time, signal, shutil, subprocess

def get_pid2( process_name ):
    """
    Get PID of a process.
    @process_name: Name of the process.
    """
    pid = None

    try:
        p1 = subprocess.Popen( [ "pidof", process_name ], stdout = subprocess.PIPE, stderr = subprocess.PIPE )
        pid = p1.communicate()[0].strip()
    except Exception as e:
        print e

    return pid

def get_pid( process_name ):
    """
    Get PID of a process.
    @process_name: Name of the process.
    """
    pid = None

    try:
        p1 = subprocess.Popen( [ "vsh", "-c", "show processes cpu" ], stdout = subprocess.PIPE )
        output_lines = p1.communicate()[0].split('\n')

        rExpConfElem = re.compile( "^.*" + process_name + ".*$" )

        for line in output_lines:
            m = rExpConfElem.match( line )

            if m != None:
                pid = line.split()[0].strip()
                break
    except:
        pid = None

    return pid

def reverse_readline( file_name, buf_size = 2048 ):
    """
    A generator that returns the lines of a file in reverse order.
    """
    with open( file_name ) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        total_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(total_size, offset + buf_size)
            fh.seek(-offset, os.SEEK_END)
            buffer = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buffer.split('\n')

            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first
                if buffer[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield segment

            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                line_size = len(lines[index])
                if line_size:
                    yield lines[index]

        yield segment

def get_mo_configs( dn ):
    """
    Get the properties of the MO and print interested values.
    @dn: DN of the MO
    """
    try:
        env = os.environ
        env[ 'DME_MANUAL_TEST' ] = '1'
        exp = re.compile( '^[ ]*"(.*Cfg.*)" : "(.*)"$' )

        print "DN:\t", dn
        print "Retrieving MO properties ..."

        p1 = subprocess.Popen( [ "xtf_dme_test", "-D", "dn=" + dn, "manual", "lookup" ], stdout = subprocess.PIPE, stderr = subprocess.PIPE, env=env )
        output_lines = p1.communicate()[0].split('\n')

        print "PROPERTIES:"
        for line in output_lines:
            match = exp.match( line )
            if match != None:
                ps = match.group(2).split(',')
                print match.group(1)
                for i in range( len( ps )):
                    print "\t {}".format( ps[i] )

    except Exception as e:
        print e

def get_retry_info():
    """
    A function to parse conf-element logs and show retry info
    """
    reRetryNotEmpty = re.compile( "^.*cfgctrl.*RetryMap not empty.*$" )
    reRetryEmpty    = re.compile( "^.*cfgctrl.*RetryMap empty.*$" )
    reRetryNumElem  = re.compile( "^.*cfgctrl.*Retry map num elements: (.*) \(.*$" )
    reRetrySending  = re.compile( "^.*cfgctrl.*Sending .* retry for (.*) \(.*$")

    #pid = get_pid( "confelem" )
    pid = get_pid2( "svc_ifc_confelem" )

    if pid == None:
        print "ERROR: unable to determine PID of svc_ifc_confelem"
        return
    #print "PID svc_ifc_confelem:", pid

    file_name     = "/nxos/dme_logs/svc_ifc_confelem.{0}.log".format( pid )
    file_name_tmp = "/nxos/dme_logs/svc_ifc_confelem.{0}.tmp.log".format( pid )
    shutil.copyfile( file_name, file_name_tmp )
    #print "Copy of log file created:", file_name_tmp

    lines = []
    for line in reverse_readline( file_name_tmp ):
        lines.insert( 0, line )

        if reRetryNotEmpty.match( line ):
            retry_entry_found = True;
            break
        elif reRetryEmpty.match( line ):
            retry_entry_found = False
            break

    if retry_entry_found == True:
        m = reRetryNumElem.match( lines[ 1 ])

        if m != None:
            print "Retry is ongoing for the following", m.group(1), "objects:"
        else:
            print "Retry is ongoing for the following objects:"
        print "=============================================="

        for i in xrange(2, len( lines )):
            m = reRetrySending.match( lines[i] )
            if m == None:
                continue
            
            # group(1) may contain dn as well as other
            # string so filter it
            dn = m.group(1).split()[0]

            get_mo_configs( dn )
            print "----------------------------------------------"
    else:
        print "No retry entry found."

    # remove tmp log file
    os.remove( file_name_tmp )

def get_conf_element_retry_info():
    try:
        get_retry_info()
    except KeyboardInterrupt:
        print "Keyboard intrrupt !"

if __name__ == "__main__":
    get_conf_element_retry_info()
