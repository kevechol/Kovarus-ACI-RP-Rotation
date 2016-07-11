# This file was automatically generated by SWIG (http://www.swig.org).
# Version 2.0.10
#
#    Copyright (c) 2015 by Cisco Systems, Inc.
#    All rights reserved.
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.



from sys import version_info
if version_info >= (2,6,0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_libnxos_ext_api', [dirname(__file__)])
        except ImportError:
            import _libnxos_ext_api
            return _libnxos_ext_api
        if fp is not None:
            try:
                _mod = imp.load_module('_libnxos_ext_api', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _libnxos_ext_api = swig_import_helper()
    del swig_import_helper
else:
    import _libnxos_ext_api
del version_info
try:
    _swig_property = property
except NameError:
    pass # Python < 2.2 doesn't have 'property'.
def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "thisown"): return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    if (name == "thisown"): return self.this.own()
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError(name)

def _swig_repr(self):
    try: strthis = "proxy of " + self.this.__repr__()
    except: strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0



def new_uint8p():
  return _libnxos_ext_api.new_uint8p()
new_uint8p = _libnxos_ext_api.new_uint8p

def copy_uint8p(*args):
  return _libnxos_ext_api.copy_uint8p(*args)
copy_uint8p = _libnxos_ext_api.copy_uint8p

def delete_uint8p(*args):
  return _libnxos_ext_api.delete_uint8p(*args)
delete_uint8p = _libnxos_ext_api.delete_uint8p

def uint8p_assign(*args):
  return _libnxos_ext_api.uint8p_assign(*args)
uint8p_assign = _libnxos_ext_api.uint8p_assign

def uint8p_value(*args):
  return _libnxos_ext_api.uint8p_value(*args)
uint8p_value = _libnxos_ext_api.uint8p_value

def new_uint32p():
  return _libnxos_ext_api.new_uint32p()
new_uint32p = _libnxos_ext_api.new_uint32p

def copy_uint32p(*args):
  return _libnxos_ext_api.copy_uint32p(*args)
copy_uint32p = _libnxos_ext_api.copy_uint32p

def delete_uint32p(*args):
  return _libnxos_ext_api.delete_uint32p(*args)
delete_uint32p = _libnxos_ext_api.delete_uint32p

def uint32p_assign(*args):
  return _libnxos_ext_api.uint32p_assign(*args)
uint32p_assign = _libnxos_ext_api.uint32p_assign

def uint32p_value(*args):
  return _libnxos_ext_api.uint32p_value(*args)
uint32p_value = _libnxos_ext_api.uint32p_value

def new_uintArray(*args):
  return _libnxos_ext_api.new_uintArray(*args)
new_uintArray = _libnxos_ext_api.new_uintArray

def delete_uintArray(*args):
  return _libnxos_ext_api.delete_uintArray(*args)
delete_uintArray = _libnxos_ext_api.delete_uintArray

def uintArray_getitem(*args):
  return _libnxos_ext_api.uintArray_getitem(*args)
uintArray_getitem = _libnxos_ext_api.uintArray_getitem

def uintArray_setitem(*args):
  return _libnxos_ext_api.uintArray_setitem(*args)
uintArray_setitem = _libnxos_ext_api.uintArray_setitem

def new_ucharArray(*args):
  return _libnxos_ext_api.new_ucharArray(*args)
new_ucharArray = _libnxos_ext_api.new_ucharArray

def delete_ucharArray(*args):
  return _libnxos_ext_api.delete_ucharArray(*args)
delete_ucharArray = _libnxos_ext_api.delete_ucharArray

def ucharArray_getitem(*args):
  return _libnxos_ext_api.ucharArray_getitem(*args)
ucharArray_getitem = _libnxos_ext_api.ucharArray_getitem

def ucharArray_setitem(*args):
  return _libnxos_ext_api.ucharArray_setitem(*args)
ucharArray_setitem = _libnxos_ext_api.ucharArray_setitem

def py_im_get_pc_membership(*args):
  return _libnxos_ext_api.py_im_get_pc_membership(*args)
py_im_get_pc_membership = _libnxos_ext_api.py_im_get_pc_membership

def py_im_get_ifindex_oper_status(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_status(*args)
py_im_get_ifindex_oper_status = _libnxos_ext_api.py_im_get_ifindex_oper_status

def py_im_get_ifindex_oper_speed(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_speed(*args)
py_im_get_ifindex_oper_speed = _libnxos_ext_api.py_im_get_ifindex_oper_speed

def py_im_get_ifindex_oper_duplex(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_duplex(*args)
py_im_get_ifindex_oper_duplex = _libnxos_ext_api.py_im_get_ifindex_oper_duplex

def py_im_get_ifindex_layermode_list(*args):
  return _libnxos_ext_api.py_im_get_ifindex_layermode_list(*args)
py_im_get_ifindex_layermode_list = _libnxos_ext_api.py_im_get_ifindex_layermode_list

def test_func(*args):
  return _libnxos_ext_api.test_func(*args)
test_func = _libnxos_ext_api.test_func

def py_im_get_iod_frm_ifindex(*args):
  return _libnxos_ext_api.py_im_get_iod_frm_ifindex(*args)
py_im_get_iod_frm_ifindex = _libnxos_ext_api.py_im_get_iod_frm_ifindex

def py_im_get_ifindex_oper_state(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_state(*args)
py_im_get_ifindex_oper_state = _libnxos_ext_api.py_im_get_ifindex_oper_state

def py_im_get_ifindex_oper_vlans(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_vlans(*args)
py_im_get_ifindex_oper_vlans = _libnxos_ext_api.py_im_get_ifindex_oper_vlans

def py_im_get_ifindex_oper_vlans_ordered(*args):
  return _libnxos_ext_api.py_im_get_ifindex_oper_vlans_ordered(*args)
py_im_get_ifindex_oper_vlans_ordered = _libnxos_ext_api.py_im_get_ifindex_oper_vlans_ordered

def py_mcecm_is_peer_mcec_up(*args):
  return _libnxos_ext_api.py_mcecm_is_peer_mcec_up(*args)
py_mcecm_is_peer_mcec_up = _libnxos_ext_api.py_mcecm_is_peer_mcec_up

def py_get_peer_mcec_up_vlans(*args):
  return _libnxos_ext_api.py_get_peer_mcec_up_vlans(*args)
py_get_peer_mcec_up_vlans = _libnxos_ext_api.py_get_peer_mcec_up_vlans

def py_mcecm_api_is_pc_mcec(*args):
  return _libnxos_ext_api.py_mcecm_api_is_pc_mcec(*args)
py_mcecm_api_is_pc_mcec = _libnxos_ext_api.py_mcecm_api_is_pc_mcec

def py_mcecm_api_is_pc_mct(*args):
  return _libnxos_ext_api.py_mcecm_api_is_pc_mct(*args)
py_mcecm_api_is_pc_mct = _libnxos_ext_api.py_mcecm_api_is_pc_mct

def py_get_mcec_num(*args):
  return _libnxos_ext_api.py_get_mcec_num(*args)
py_get_mcec_num = _libnxos_ext_api.py_get_mcec_num

def py_get_mct_ifindex():
  return _libnxos_ext_api.py_get_mct_ifindex()
py_get_mct_ifindex = _libnxos_ext_api.py_get_mct_ifindex

def py_im_get_hw_info_from_if_name(*args):
  return _libnxos_ext_api.py_im_get_hw_info_from_if_name(*args)
py_im_get_hw_info_from_if_name = _libnxos_ext_api.py_im_get_hw_info_from_if_name

def py_im_is_ifindex_ranger_attached(*args):
  return _libnxos_ext_api.py_im_is_ifindex_ranger_attached(*args)
py_im_is_ifindex_ranger_attached = _libnxos_ext_api.py_im_is_ifindex_ranger_attached

def py_im_get_if_name_and_if_index_from_mod_unit_port(*args):
  return _libnxos_ext_api.py_im_get_if_name_and_if_index_from_mod_unit_port(*args)
py_im_get_if_name_and_if_index_from_mod_unit_port = _libnxos_ext_api.py_im_get_if_name_and_if_index_from_mod_unit_port

def py_get_fport_mods_for_hif(*args):
  return _libnxos_ext_api.py_get_fport_mods_for_hif(*args)
py_get_fport_mods_for_hif = _libnxos_ext_api.py_get_fport_mods_for_hif

def py_im_get_if_index_from_vp(*args):
  return _libnxos_ext_api.py_im_get_if_index_from_vp(*args)
py_im_get_if_index_from_vp = _libnxos_ext_api.py_im_get_if_index_from_vp

def py_im_get_vp_from_if_index(*args):
  return _libnxos_ext_api.py_im_get_vp_from_if_index(*args)
py_im_get_vp_from_if_index = _libnxos_ext_api.py_im_get_vp_from_if_index

def py_mts_init():
  return _libnxos_ext_api.py_mts_init()
py_mts_init = _libnxos_ext_api.py_mts_init

def py_im_get_if_index_from_name(*args):
  return _libnxos_ext_api.py_im_get_if_index_from_name(*args)
py_im_get_if_index_from_name = _libnxos_ext_api.py_im_get_if_index_from_name

def py_im_is_ifindex_linkup(*args):
  return _libnxos_ext_api.py_im_is_ifindex_linkup(*args)
py_im_is_ifindex_linkup = _libnxos_ext_api.py_im_is_ifindex_linkup

def py_im_get_ifindex_mtu(*args):
  return _libnxos_ext_api.py_im_get_ifindex_mtu(*args)
py_im_get_ifindex_mtu = _libnxos_ext_api.py_im_get_ifindex_mtu

def py_eltm_get_ifindex_vrf_id(*args):
  return _libnxos_ext_api.py_eltm_get_ifindex_vrf_id(*args)
py_eltm_get_ifindex_vrf_id = _libnxos_ext_api.py_eltm_get_ifindex_vrf_id

def py_im_get_long_name_from_if_index(*args):
  return _libnxos_ext_api.py_im_get_long_name_from_if_index(*args)
py_im_get_long_name_from_if_index = _libnxos_ext_api.py_im_get_long_name_from_if_index

def py_im_get_short_name_from_if_index(*args):
  return _libnxos_ext_api.py_im_get_short_name_from_if_index(*args)
py_im_get_short_name_from_if_index = _libnxos_ext_api.py_im_get_short_name_from_if_index

def py_pfm_is_module_online(*args):
  return _libnxos_ext_api.py_pfm_is_module_online(*args)
py_pfm_is_module_online = _libnxos_ext_api.py_pfm_is_module_online

def py_syslog(*args):
  return _libnxos_ext_api.py_syslog(*args)
py_syslog = _libnxos_ext_api.py_syslog

def py_im_get_ifindex_admin_status(*args):
  return _libnxos_ext_api.py_im_get_ifindex_admin_status(*args)
py_im_get_ifindex_admin_status = _libnxos_ext_api.py_im_get_ifindex_admin_status

def py_im_get_pc(*args):
  return _libnxos_ext_api.py_im_get_pc(*args)
py_im_get_pc = _libnxos_ext_api.py_im_get_pc

def py_im_get_vif_from_if_index(*args):
  return _libnxos_ext_api.py_im_get_vif_from_if_index(*args)
py_im_get_vif_from_if_index = _libnxos_ext_api.py_im_get_vif_from_if_index

def py_im_get_ifindex_real_port_mode(*args):
  return _libnxos_ext_api.py_im_get_ifindex_real_port_mode(*args)
py_im_get_ifindex_real_port_mode = _libnxos_ext_api.py_im_get_ifindex_real_port_mode

def py_vlan_mgr_sdb_get_vlan_segment_id(*args):
  return _libnxos_ext_api.py_vlan_mgr_sdb_get_vlan_segment_id(*args)
py_vlan_mgr_sdb_get_vlan_segment_id = _libnxos_ext_api.py_vlan_mgr_sdb_get_vlan_segment_id

def py_pixm_lib_ifidx_to_di(*args):
  return _libnxos_ext_api.py_pixm_lib_ifidx_to_di(*args)
py_pixm_lib_ifidx_to_di = _libnxos_ext_api.py_pixm_lib_ifidx_to_di

def py_pixm_lib_vlan_to_mct_syn_ifidx(*args):
  return _libnxos_ext_api.py_pixm_lib_vlan_to_mct_syn_ifidx(*args)
py_pixm_lib_vlan_to_mct_syn_ifidx = _libnxos_ext_api.py_pixm_lib_vlan_to_mct_syn_ifidx

def py_pixm_lib_ifidx_vlan_to_vp(*args):
  return _libnxos_ext_api.py_pixm_lib_ifidx_vlan_to_vp(*args)
py_pixm_lib_ifidx_vlan_to_vp = _libnxos_ext_api.py_pixm_lib_ifidx_vlan_to_vp

def py_get_fpc_ifidx_for_hif(*args):
  return _libnxos_ext_api.py_get_fpc_ifidx_for_hif(*args)
py_get_fpc_ifidx_for_hif = _libnxos_ext_api.py_get_fpc_ifidx_for_hif

def py_if_index_vpl(*args):
  return _libnxos_ext_api.py_if_index_vpl(*args)
py_if_index_vpl = _libnxos_ext_api.py_if_index_vpl

def py_im_is_ifindex_access_port(*args):
  return _libnxos_ext_api.py_im_is_ifindex_access_port(*args)
py_im_is_ifindex_access_port = _libnxos_ext_api.py_im_is_ifindex_access_port

def py_im_is_ifindex_dot1q_port(*args):
  return _libnxos_ext_api.py_im_is_ifindex_dot1q_port(*args)
py_im_is_ifindex_dot1q_port = _libnxos_ext_api.py_im_is_ifindex_dot1q_port

def py_im_is_port_span_dest(*args):
  return _libnxos_ext_api.py_im_is_port_span_dest(*args)
py_im_is_port_span_dest = _libnxos_ext_api.py_im_is_port_span_dest

def py_im_is_port_up(*args):
  return _libnxos_ext_api.py_im_is_port_up(*args)
py_im_is_port_up = _libnxos_ext_api.py_im_is_port_up

def py_platform_is_fabric_unit(*args):
  return _libnxos_ext_api.py_platform_is_fabric_unit(*args)
py_platform_is_fabric_unit = _libnxos_ext_api.py_platform_is_fabric_unit

def py_platform_is_lacrosse(*args):
  return _libnxos_ext_api.py_platform_is_lacrosse(*args)
py_platform_is_lacrosse = _libnxos_ext_api.py_platform_is_lacrosse

def py_platform_is_davos(*args):
  return _libnxos_ext_api.py_platform_is_davos(*args)
py_platform_is_davos = _libnxos_ext_api.py_platform_is_davos

def py_im_get_hw_info_from_slice_info(*args):
  return _libnxos_ext_api.py_im_get_hw_info_from_slice_info(*args)
py_im_get_hw_info_from_slice_info = _libnxos_ext_api.py_im_get_hw_info_from_slice_info

def py_im_get_hw_info_from_src_id_info(*args):
  return _libnxos_ext_api.py_im_get_hw_info_from_src_id_info(*args)
py_im_get_hw_info_from_src_id_info = _libnxos_ext_api.py_im_get_hw_info_from_src_id_info

def py_im_get_ifindex_from_vif(*args):
  return _libnxos_ext_api.py_im_get_ifindex_from_vif(*args)
py_im_get_ifindex_from_vif = _libnxos_ext_api.py_im_get_ifindex_from_vif

def py_vlan_get_oper_original_vlan(*args):
  return _libnxos_ext_api.py_vlan_get_oper_original_vlan(*args)
py_vlan_get_oper_original_vlan = _libnxos_ext_api.py_vlan_get_oper_original_vlan

def py_vlan_get_oper_translated_vlan(*args):
  return _libnxos_ext_api.py_vlan_get_oper_translated_vlan(*args)
py_vlan_get_oper_translated_vlan = _libnxos_ext_api.py_vlan_get_oper_translated_vlan

def py_get_inseor_vpl_vp_min():
  return _libnxos_ext_api.py_get_inseor_vpl_vp_min()
py_get_inseor_vpl_vp_min = _libnxos_ext_api.py_get_inseor_vpl_vp_min

def py_libltlmap_vpl_pool_begin():
  return _libnxos_ext_api.py_libltlmap_vpl_pool_begin()
py_libltlmap_vpl_pool_begin = _libnxos_ext_api.py_libltlmap_vpl_pool_begin

def py_nve_peer_id_from_peer_ip(*args):
  return _libnxos_ext_api.py_nve_peer_id_from_peer_ip(*args)
py_nve_peer_id_from_peer_ip = _libnxos_ext_api.py_nve_peer_id_from_peer_ip
# This file is compatible with both classic and new-style classes.

cvar = _libnxos_ext_api.cvar
