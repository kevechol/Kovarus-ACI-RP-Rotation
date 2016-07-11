#!/router/bin/python
search_files = ['interface.py','module.py','mcast.py']
global_tags = []
import fuzz
best_info = []

def process_file_tags(_fname, _line):
    strs = _line[5:].split(',')
    for s in strs:
        global_tags.append((s,_fname))

def search_debug_scripts(_info, _search_strings):
    for f in search_files:
        readlines = file("/isan/python/scripts/" + f)
        for line in readlines:
            if "#TAGS:" in line:
                process_file_tags(f, line)
                break

    for srch in _search_strings:
        last_best = 30
        best = 0
        #we will grep in our scripts to find out the best match.
        for (s,f) in global_tags: 
            best = fuzz.ratio(s,srch)
            if best >= last_best:
                last_best = best
                best_info.append((best,s,f))


    best_info.reverse()
    once = []

    print "Found following scripts in order of relevance:"
    print "----------------------------------------------"
    for (score, s, f) in best_info:
        if f not in once:
            print " (%d)"%score, f
            once.append(f)
    print "----------------------------------------------"
    print ""
    print ""
    print "Note:"

    print " To display info about script and its functions, do:"
    print "    python"
    print "    import module"
    print "    dir(module)"
    print "    print module.debug_module_reload_delays.func_doc"

    return best_info            

