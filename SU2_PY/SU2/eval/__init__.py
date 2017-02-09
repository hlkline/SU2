
from functions import function as func
from functions import aerodynamics, geometry
from gradients import gradient as grad
from gradients import adjoint, findiff
from design import Design, \
     obj_f, obj_df,        \
     obj_p, obj_dp,        \
     con_ceq, con_dceq,    \
     con_cieq, con_dcieq,  \
     touch, skip