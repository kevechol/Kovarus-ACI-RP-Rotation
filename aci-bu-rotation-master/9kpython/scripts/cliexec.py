import sys, imp
import traceback

def executor(modpath, modname, args):           
    print 'Class = ',modname,' Path = ', modpath
    for t in args:                              
        print 'Type: ',t[0]                     
        print 'Label: ',t[1]                    
        print 'Value: ',t[2]                         
    if not modpath:                                      
        modpath = '/isan/python/scripts/modus'
    print 'modpath=', modpath
    try:                     
	list = modname.split('.')
	print list[0], list[1]                          
        print "loading module"                         
        py_mod = imp.load_source(list[0], modpath+'/'+list[0]+'.py' )
        if hasattr(py_mod, list[1]):
            class_inst = getattr(py_mod, list[1])
            print "invoking module.class(args)"
            class_inst(args)
    except:                                            
        tb = traceback.format_exc()
	sys.exit(1)
    else:                          
        tb = "No error"            
    finally:                       
        print tb                     

if __name__ == "__main__":         
    t = ('keyword', 'pycli', 'pycli')
    args = []                        
    args.append(t)                   
    executor('/isan/python/scripts/modus', 'Example.Example1', args)
