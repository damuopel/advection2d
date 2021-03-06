import numpy as np
from numpy.linalg import inv,det
from math import floor
from scipy.sparse import csc_matrix,linalg

def Mesh(eSize,xElms,yElms):
    # Coordinates
    start = 0
    xStop = eSize*xElms
    yStop = eSize*yElms
    x = np.linspace(start,xStop,xElms+1)
    y = np.linspace(start,yStop,yElms+1)
    X,Y = np.meshgrid(x,y)
    XY = np.array([X.flatten(),Y.flatten()])
    # Topology
    node1 = np.array([iElm+floor(iElm/xElms) for iElm in range(xElms*yElms)])
    node2 = node1 + 1
    node3 = node2 + xElms + 1
    node4 = node1 + xElms + 1
    Topology = np.array([node1,node2,node3,node4])

    return Topology,XY

def ShapeFunctions(Xi,Eta,dFlag):
    if dFlag==1:
        dN1dXi = -0.25*(1-Eta)
        dN1dEta = -0.25*(1-Xi)
        dN2dXi = 0.25*(1-Eta)
        dN2dEta = -0.25*(1+Xi)
        dN3dXi = 0.25*(1+Eta)
        dN3dEta = 0.25*(1+Xi)
        dN4dXi = -0.25*(1+Eta)
        dN4dEta = 0.25*(1-Xi)
        N = np.array([[dN1dXi,dN2dXi,dN3dXi,dN4dXi],[dN1dEta,dN2dEta,dN3dEta,dN4dEta]])
    else:
        N1 = 0.25*(1-Xi)*(1-Eta)
        N2 = 0.25*(1+Xi)*(1-Eta)
        N3 = 0.25*(1+Xi)*(1+Eta)
        N4 = 0.25*(1-Xi)*(1+Eta)
        N = np.array([N1,N2,N3,N4])
            
    return N

def D_Matrix(E,nu):
    # PLain Stress
    D = (E/(1-nu**2))*np.array([[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]])
    
    return D

def K_Matrix(Topology,XY,D,thickness):
    # Integration
    allDofs = int(XY.size/2)*2
    nElms = int(Topology.size/4)
    dofsElements = 8
    # Initialize some variables
    xyGPI = np.array([[-0.5774,-0.5774,0.5774,0.5774],[-0.5774,0.5774,-0.5774,0.5774]])
    hGPI = np.array([1,1,1,1])
    refNodes = Topology[:,0]# Pick a reference element (are the same)
    refVerts = XY[:,refNodes]
    Ke = 0
    for iGP in range(4):
        Xi = xyGPI[0,iGP]
        Eta = xyGPI[1,iGP]
        H = hGPI[iGP]
        dNl = ShapeFunctions(Xi,Eta,1)
        Jacobian = refVerts@dNl.T
        dNg = inv(Jacobian)@dNl
        B = np.array([[dNg[0,0],0,dNg[0,1],0,dNg[0,2],0,dNg[0,3],0],[0,dNg[1,0],0,dNg[1,1],0,dNg[1,2],0,dNg[1,3]],[dNg[1,0],dNg[0,0],dNg[1,1],dNg[0,1],dNg[1,2],dNg[0,2],dNg[1,3],dNg[0,3]]])
        BtD = np.dot(B.T,D)
        Ke = Ke + thickness*np.dot(BtD,B)*det(Jacobian)*H  
    # Assembly
    elsDofs = 2*np.kron(Topology,np.ones((2,1)))+np.tile(np.array([[0],[1]]),[4,nElms])
    row = np.kron(elsDofs,np.ones((1,dofsElements))).T.flatten()
    col = np.kron(elsDofs,np.ones((dofsElements,1))).T.flatten()
    data = np.tile(Ke.flatten(),nElms).flatten()
    K = csc_matrix((data,(row,col)),shape=(allDofs,allDofs)) 

    return K

def F_Array(Topology,XY):
    dofs = int(XY.size/2)*2
    F = np.zeros((dofs,1))
    Case = 'Puntual Force'
    if Case == 'Puntual Force':
        # Punctual Force
        maxValues = XY.max(1)
        xMax = XY[0,:]==maxValues[0]
        minValues = XY.min(1)
        yMin = XY[1,:]==minValues[1]
        nodes = np.arange(int(XY.size/2))
        forceNodes = nodes[np.where(np.logical_and(xMax,yMin))]
        forceDofs = np.array([2*forceNodes,2*forceNodes+1])
        fx = 0
        fy = -1
        F[forceDofs[0,:]] = fx
        F[forceDofs[1,:]] = fy
        
    return F    

def Solver(K,F,Topology,XY):
    dofs = int(XY.size/2)*2
    totalDofs = np.arange(dofs)
    Case = 'Clamp'
    if Case == 'Clamp':
        minValues = XY.min(1)
        xMin = XY[0,:]==minValues[0]
        restNodes = np.where(xMin)[0]
        restDofs = np.array([2*restNodes,2*restNodes+1]).T.flatten()
        uRest = np.zeros((restDofs.size,1))
        freeDofs = np.setdiff1d(totalDofs,restDofs)
        
    freeDofsX,freeDofsY = np.meshgrid(freeDofs,freeDofs)
    frDofsX,frDofsY = np.meshgrid(restDofs,freeDofs)
    u = np.zeros((dofs,1))
    uFree = linalg.inv(K[freeDofsX,freeDofsY])*F[freeDofs]-K[frDofsX,frDofsY]*uRest
    u[freeDofs] = uFree
    u[restDofs] = uRest
    
    return u

