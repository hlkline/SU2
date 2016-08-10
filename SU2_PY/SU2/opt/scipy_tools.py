#!/usr/bin/env python 

## \file scipy_tools.py
#  \brief tools for interfacing with scipy
#  \author T. Lukaczyk, F. Palacios
#  \version 4.2.0 "Cardinal"
#
# SU2 Lead Developers: Dr. Francisco Palacios (Francisco.D.Palacios@boeing.com).
#                      Dr. Thomas D. Economon (economon@stanford.edu).
#
# SU2 Developers: Prof. Juan J. Alonso's group at Stanford University.
#                 Prof. Piero Colonna's group at Delft University of Technology.
#                 Prof. Nicolas R. Gauger's group at Kaiserslautern University of Technology.
#                 Prof. Alberto Guardone's group at Polytechnic University of Milan.
#                 Prof. Rafael Palacios' group at Imperial College London.
#
# Copyright (C) 2012-2016 SU2, the open-source CFD code.
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

# -------------------------------------------------------------------
#  Imports
# -------------------------------------------------------------------

import os, sys, shutil, copy

from .. import eval as su2eval
from numpy import array, zeros
from numpy.linalg import norm


# -------------------------------------------------------------------
#  pyOpt Optimizers
# -------------------------------------------------------------------
# format needed by pyopt
def obj_func(x, *args, **kwargs):
    project = kwargs['p1']
    f = obj_f(x,project)
    g = 0.0
    fail = 0
    return f,g,fail

def grad_func(x,f,g, *args, **kwargs):
    project = kwargs['p1']
    g_obj = [0.0]*project.n_dv
    grad = obj_df(x,project)
    for i in range(project.n_dv):
        g_obj[i] =grad[i]
    g_con=zeros([1,project.n_dv])
    fail = 0
    return g_obj, g_con, fail


# -------------------------------------------------------------------
#  pyOpt SLSQP
# -------------------------------------------------------------------
def pyopt_snopt(project,x0=None,xb=None,its=100,accu=1e-10,maxstep=1e-3,partialprice=1, grads=True):
    """ result = scipy_slsqp(project,x0=[],xb=[],its=100,accu=1e-10)
    
        Runs the Scipy implementation of SLSQP with 
        an SU2 project
        
        Inputs:
            project - an SU2 project
            x0      - optional, initial guess
            xb      - optional, design variable bounds
            its     - max outer iterations, default 100
            accu    - accuracy, default 1e-10
        
        Outputs:
           result - the outputs from scipy.fmin_slsqp
    """
        # import scipy optimizer
    import pyOpt
    from pyOpt import pySNOPT
    # handle input cases
    if x0 is None: x0 = []
    if xb is None: xb = []
    
    # function handles
    func           = obj_f
    f_eqcons       = con_ceq
    f_ieqcons      = con_cieq 
    
    # gradient handles
    if project.config.get('GRADIENT_METHOD','NONE') == 'NONE': 
        fprime         = None
        fprime_eqcons  = None
        fprime_ieqcons = None
    else:
        fprime         = obj_df
        fprime_eqcons  = con_dceq
        fprime_ieqcons = con_dcieq        
    
    # number of design variables
    n_dv = len( project.config['DEFINITION_DV']['KIND'] )
    project.n_dv = n_dv
    
    # Initial guess
    if not x0: x0 = [0.0]*n_dv
    
    # prescale x0
    dv_scales = project.config['DEFINITION_DV']['SCALE']
    x0 = [ x0[i]/dv_scl for i,dv_scl in enumerate(dv_scales) ]    
    
    # scale accuracy
    obj = project.config['OPT_OBJECTIVE']
    obj_scale = []
    for this_obj in obj.keys():
        obj_scale = obj_scale + [obj[this_obj]['SCALE']]
    
    accu = accu*obj_scale[0]

    # scale accuracy
    eps = 1.0e-04

    # optimizer summary
    sys.stdout.write('SNOPT parameters:\n')
    sys.stdout.write('Number of design variables: ' + str(n_dv) + '\n')
    sys.stdout.write('Objective function scaling factor: ' + str(obj_scale) + '\n')
    sys.stdout.write('Maximum number of iterations: ' + str(its) + '\n')
    sys.stdout.write('Requested accuracy: ' + str(accu) + '\n')
    sys.stdout.write('Initial guess for the independent variable(s): ' + str(x0) + '\n')
    sys.stdout.write('Lower and upper bound for each independent variable: ' + str(xb) + '\n\n')

    lb = [0.0]*n_dv
    ub = [0.0]*n_dv
    for i in range(n_dv):
        lb[i] = xb[i][0]
        ub[i] = xb[i][1]
    
    opt_prob = pyOpt.Optimization('SNOPT constrained optimization problem',obj_func, use_groups=True)
    opt_prob.addVarGroup('x',n_dv,'c',lower=lb[0], upper=ub[0],value=x0[0] )
    opt_prob.addObj('f')
    print opt_prob
    snopt = pySNOPT.SNOPT(options = {'Partial price': partialprice,'Elastic mode':'Yes','Linesearch tolerance':0.99,'Major step limit':maxstep,'Major optimality tolerance':accu, 'Elastic weight':1.0e-6, 'Verify level':-1, 'Nonderivative linesearch':None})

    # Run Optimizer
    [fstr, xstr, inform] = snopt(opt_prob,sens_type=grad_func,p1=project)

    print opt_prob.solution(0)

    # Done
    return fstr

    


# -------------------------------------------------------------------
#  pyOpt SLSQP
# -------------------------------------------------------------------
def pyopt_slsqp(project,x0=None,xb=None,its=100,accu=1e-10,grads=True):
    """ result = scipy_slsqp(project,x0=[],xb=[],its=100,accu=1e-10)
    
        Runs the Scipy implementation of SLSQP with 
        an SU2 project
        
        Inputs:
            project - an SU2 project
            x0      - optional, initial guess
            xb      - optional, design variable bounds
            its     - max outer iterations, default 100
            accu    - accuracy, default 1e-10
        
        Outputs:
           result - the outputs from scipy.fmin_slsqp
    """
        # import scipy optimizer
    import pyOpt
    
    # handle input cases
    if x0 is None: x0 = []
    if xb is None: xb = []
    
    # function handles
    func           = obj_f
    f_eqcons       = con_ceq
    f_ieqcons      = con_cieq 
    
    # gradient handles
    if project.config.get('GRADIENT_METHOD','NONE') == 'NONE': 
        fprime         = None
        fprime_eqcons  = None
        fprime_ieqcons = None
    else:
        fprime         = obj_df
        fprime_eqcons  = con_dceq
        fprime_ieqcons = con_dcieq        
    
    # number of design variables
    n_dv = len( project.config['DEFINITION_DV']['KIND'] )
    project.n_dv = n_dv
    
    # Initial guess
    if not x0: x0 = [0.0]*n_dv
    
    # prescale x0
    dv_scales = project.config['DEFINITION_DV']['SCALE']
    x0 = [ x0[i]/dv_scl for i,dv_scl in enumerate(dv_scales) ]    
    
    # scale accuracy
    obj = project.config['OPT_OBJECTIVE']
    obj_scale = []
    for this_obj in obj.keys():
        obj_scale = obj_scale + [obj[this_obj]['SCALE']]
    
    accu = accu*obj_scale[0]

    # scale accuracy
    eps = 1.0e-04

    # optimizer summary
    sys.stdout.write('SLSQP parameters:\n')
    sys.stdout.write('Number of design variables: ' + str(n_dv) + '\n')
    sys.stdout.write('Objective function scaling factor: ' + str(obj_scale) + '\n')
    sys.stdout.write('Maximum number of iterations: ' + str(its) + '\n')
    sys.stdout.write('Requested accuracy: ' + str(accu) + '\n')
    sys.stdout.write('Initial guess for the independent variable(s): ' + str(x0) + '\n')
    sys.stdout.write('Lower and upper bound for each independent variable: ' + str(xb) + '\n\n')

    lb = [0.0]*n_dv
    ub = [0.0]*n_dv
    for i in range(n_dv):
        lb[i] = xb[i][0]
        ub[i] = xb[i][1]
    
    opt_prob = pyOpt.Optimization('pyOpt SLSQP',obj_func, use_groups=True)
    opt_prob.addVarGroup('x',n_dv,'c',lower=lb[0], upper=ub[0],value=x0[0] )
    opt_prob.addObj('f')
    print opt_prob
    
    slsqp = pyOpt.SLSQP()
    slsqp.setOption('IPRINT',2)
    
    # Run Optimizer
    [fstr, xstr, inform] = slsqp(opt_prob,sens_type=grad_func,p1=project)

    print opt_prob.solution(0)
    
    # Done
    return fstr
    
    
# -------------------------------------------------------------------
#  Scipy SLSQP
# -------------------------------------------------------------------

def scipy_slsqp(project,x0=None,xb=None,its=100,accu=1e-10,grads=True):
    """ result = scipy_slsqp(project,x0=[],xb=[],its=100,accu=1e-10)
    
        Runs the Scipy implementation of SLSQP with 
        an SU2 project
        
        Inputs:
            project - an SU2 project
            x0      - optional, initial guess
            xb      - optional, design variable bounds
            its     - max outer iterations, default 100
            accu    - accuracy, default 1e-10
        
        Outputs:
           result - the outputs from scipy.fmin_slsqp
    """

    # import scipy optimizer
    from scipy.optimize import fmin_slsqp

    # handle input cases
    if x0 is None: x0 = []
    if xb is None: xb = []
    
    # function handles
    func           = obj_f
    f_eqcons       = con_ceq
    f_ieqcons      = con_cieq 
    
    # gradient handles
    if project.config.get('GRADIENT_METHOD','NONE') == 'NONE': 
        fprime         = None
        fprime_eqcons  = None
        fprime_ieqcons = None
    else:
        fprime         = obj_df
        fprime_eqcons  = con_dceq
        fprime_ieqcons = con_dcieq        
    
    # number of design variables
    dv_size = project.config['DEFINITION_DV']['SIZE']
    n_dv = sum( dv_size)
    project.n_dv = n_dv
    
    # Initial guess
    if not x0: x0 = [0.0]*n_dv
    
    # prescale x0
    dv_scales = project.config['DEFINITION_DV']['SCALE']
    k = 0
    for i, dv_scl in enumerate(dv_scales):
        for j in range(dv_size[i]):
            x0[k] =x0[k]/dv_scl;
            k = k + 1

    # scale accuracy
    obj = project.config['OPT_OBJECTIVE']
    obj_scale = []
    for this_obj in obj.keys():
        obj_scale = obj_scale + [obj[this_obj]['SCALE']]
    
    accu = accu*obj_scale[0]

    # scale accuracy
    eps = 1.0e-04

    # optimizer summary
    sys.stdout.write('Sequential Least SQuares Programming (SLSQP) parameters:\n')
    sys.stdout.write('Number of design variables: ' + str(len(dv_size)) + ' ( ' + str(n_dv) + ' ) \n' )
    sys.stdout.write('Objective function scaling factor: ' + str(obj_scale) + '\n')
    sys.stdout.write('Maximum number of iterations: ' + str(its) + '\n')
    sys.stdout.write('Requested accuracy: ' + str(accu) + '\n')
    sys.stdout.write('Initial guess for the independent variable(s): ' + str(x0) + '\n')
    sys.stdout.write('Lower and upper bound for each independent variable: ' + str(xb) + '\n\n')

    # Run Optimizer
    outputs = fmin_slsqp( x0             = x0             ,
                          func           = func           , 
                          f_eqcons       = f_eqcons       , 
                          f_ieqcons      = f_ieqcons      ,
                          fprime         = fprime         ,
                          fprime_eqcons  = fprime_eqcons  , 
                          fprime_ieqcons = fprime_ieqcons , 
                          args           = (project,)     , 
                          bounds         = xb             ,
                          iter           = its            ,
                          iprint         = 2              ,
                          full_output    = True           ,
                          acc            = accu           ,
                          epsilon        = eps            )
    
    # Done
    return outputs
    
    
def obj_f(x,project):
    """ obj = obj_f(x,project)
        
        Objective Function
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         minimize f(x), list[nobj]
        scipy_slsqp: minimize f(x), float
    """
        
    obj_list = project.obj_f(x)
    obj = 0
    for this_obj in obj_list:
        obj = obj+this_obj
    
    return obj

def obj_df(x,project):
    """ dobj = obj_df(x,project)
        
        Objective Function Gradients
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         df(x), list[nobj x dim]
        scipy_slsqp: df(x), ndarray[dim]
    """    
    
    dobj_list = project.obj_df(x)
    dobj=[0.0]*len(dobj_list[0])
    
    for this_dobj in dobj_list:
        idv=0
        for this_dv_dobj in this_dobj:
            dobj[idv] = dobj[idv]+this_dv_dobj;
            idv+=1
    dobj = array( dobj )
    
    return dobj

def con_ceq(x,project):
    """ cons = con_ceq(x,project)
        
        Equality Constraint Functions
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         ceq(x) = 0.0, list[nceq]
        scipy_slsqp: ceq(x) = 0.0, ndarray[nceq]
    """
    
    cons = project.con_ceq(x)
    
    if cons: cons = array(cons)
    else:    cons = zeros([0])
        
    return cons

def con_dceq(x,project):
    """ dcons = con_dceq(x,project)
        
        Equality Constraint Gradients
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         dceq(x), list[nceq x dim]
        scipy_slsqp: dceq(x), ndarray[nceq x dim]
    """
    
    dcons = project.con_dceq(x)

    dim = project.n_dv
    if dcons: dcons = array(dcons)
    else:     dcons = zeros([0,dim])
    
    return dcons

def con_cieq(x,project):
    """ cons = con_cieq(x,project)
        
        Inequality Constraints
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         cieq(x) < 0.0, list[ncieq]
        scipy_slsqp: cieq(x) > 0.0, ndarray[ncieq]
    """
    
    cons = project.con_cieq(x)
    
    if cons: cons = array(cons)
    else:    cons = zeros([0])
    
    return -cons
    
def con_dcieq(x,project):
    """ dcons = con_dcieq(x,project)
        
        Inequality Constraint Gradients
        SU2 Project interface to scipy.fmin_slsqp
        
        su2:         dcieq(x), list[ncieq x dim]
        scipy_slsqp: dcieq(x), ndarray[ncieq x dim]
    """
    
    dcons = project.con_dcieq(x)
    
    dim = project.n_dv
    if dcons: dcons = array(dcons)
    else:     dcons = zeros([0,dim])
    
    return -dcons
