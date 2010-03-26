# =============================================================================
# Standard Python modules
# =============================================================================
import os, sys, string, pdb, copy, time

# =============================================================================
# External Python modules
# =============================================================================
from numpy import linspace, cos, pi, hstack, zeros, ones, sqrt, imag, interp, \
    array, real, reshape, meshgrid, dot, cross,shape,alltrue

# =============================================================================
# Extension modules
# =============================================================================

from mdo_import_helper import *
exec(import_modules('pyGeo','pyBlock','pySpline','geo_utils','mpi4py'))
exec(import_modules('pyAero_problem','pyAero_flow','pyAero_reference','pyAero_geometry'))
exec(import_modules('pySUMB','pyDummyMapping'))

print 'Warp Test'
# grid = pyBlock.pyBlock('plot3d',file_name='warp_test.xyz',file_type='ascii',order='f')
# grid.doConnectivity('warp_test.con')
# grid.fitGlobal()
# grid.writeBvol('warp_test.bvol',binary=True)
# grid.writeTecplot('warp_test.dat',tecio=True,orig=True)

grid = pyBlock.pyBlock('bvol',file_name='warp_test.bvol',file_type='binary')
grid.doConnectivity('warp_test.con')
g_index,gptr,l_index,lptr,l_sizes = grid.topo.flatten_indices()
mpiPrint('Number of Unique Nodes in Mesh: %d'%(len(grid.topo.g_index)))
#grid.writeTecplot('warp_test.dat',tecio=True,orig=True)

print ' '
print 'Generating Surface Geometry'
surface = pyGeo.pyGeo('plot3d',file_name='warp_test_surf.xyz',file_type='ascii',order='f')
surface.doConnectivity('warp_test_surf.con')
surface.fitGlobal()
#surface.writeTecplot('warp_test_surf.dat',tecio=True,coef=True,orig=False,surf_labels=True,directions=True)
#surface.addFFD('auto',nx=2,ny=3,nz=10)
#surface.FFD.writeTecplot('ffd.dat')

flow = Flow(name='Base Case',mach=0.5,alpha=2.0,beta=0.0,liftIndex=2)
ref = Reference('Baseline Reference',1.0,1.0,1.0)
geom = Geometry
test_case = AeroProblem(name='Simple Test',geom=geom,flow_set=flow,ref_set=ref)
solver = SUMB()
solver_options={'reinitialize':True,\
                'CFL':1.5,\
                'L2Convergence':1.e-10,\
                'MGCycle':'sg',\
                'MetricConversion':1.0,\
                'Discretization':'Central plus scalar dissipation',\
                'sol_restart':'no',
                'solveADjoint':'no',\
                'set Monitor':'Yes',\
                'Approx PC': 'no',\
                'Adjoint solver type': 'GMRES',\
                'adjoint relative tolerance':1e-10,\
                'adjoint absolute tolerance':1e-16,\
                'adjoint max iterations': 500,\
                'adjoint restart iteration' : 80,\
                'adjoint monitor step': 10,\
                'dissipation lumping parameter':6,\
                'Preconditioner Side': 'LEFT',\
                'Matrix Ordering': 'NestedDissection',\
                'Global Preconditioner Type': 'Additive Schwartz',\
                'Local Preconditioner Type' : 'ILU',\
                'ILU Fill Levels': 2,\
                'ASM Overlap' : 5,\
                'TS Stability': 'no'}
solver(test_case,niterations=1,grid_file='warp_test',solver_options=solver_options)

cfd_surface_points = solver.interface.Mesh.GetGlobalSurfaceCoordinates()
surface.attachSurface(cfd_surface_points[:,:,0])

#--------------  Do an ad-hoc modification --------------
# Pull out LE
for j in xrange(surface.surfs[4].Nctlv):
    surface.coef[surface.topo.l_index[4][1,j]] += [-.15,0,0]
    surface.coef[surface.topo.l_index[4][2,j]] += [-.15,0,0]

# Shrink TE
for i in xrange(surface.surfs[2].Nctlu):
    for j in xrange(surface.surfs[2].Nctlv):
        surface.coef[surface.topo.l_index[2][i,j]][1] *= .02 

# Pull Up Upper surface
for j in xrange(surface.surfs[0].Nctlv):
    surface.coef[surface.topo.l_index[0][1,j]] += [0,.03,0]
    surface.coef[surface.topo.l_index[0][2,j]] += [0,-.02,0]

# Pull Down Lower surface
for j in xrange(surface.surfs[3].Nctlv):
    surface.coef[surface.topo.l_index[3][1,j]] -= [0,.05,0]
    surface.coef[surface.topo.l_index[3][2,j]] -= [0,.04,0]

surface._updateSurfaceCoef()
surface.writeTecplot('warp_test_surf_update.dat',coef=False,tecio=True,directions=True)
# ---------------------------------------------------------

# Now do the solid warp
timeA = time.time()
solver.interface.Mesh.SetGlobalSurfaceCoordinates(surface.getSurfacePoints(0).transpose())
solver.interface.Mesh.warpMeshSolid(g_index,gptr,l_index,lptr,l_sizes)
print 'Time is:',time.time()-timeA

