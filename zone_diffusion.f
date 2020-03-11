c=======================================================================
c  Routine zone diffusion 2010
c
c  Determine les cellules se trouvant dans la zone de diffusion (effet)
c  des cellules (x1,y1,z1) et (x2,y2,z2) 
c  Retourne la matrice des cellules diffusantes (diffusion) ainsi que le nombre
c  de cellules diffusantes (ncellule)
c
c  
c------------------------------------------------------------------------
c   
c    Copyright (C) 2010  Martin Aube
c
c    This program is free software: you can redistribute it and/or modify
c    it under the terms of the GNU General Public License as published by
c    the Free Software Foundation, either version 3 of the License, or
c    (at your option) any later version.
c
c    This program is distributed in the hope that it will be useful,
c    but WITHOUT ANY WARRANTY; without even the implied warranty of
c    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
c    GNU General Public License for more details.
c
c    You should have received a copy of the GNU General Public License
c    along with this program.  If not, see <http://www.gnu.org/licenses/>.
c
c    Contact: martin.aube@cegepsherbrooke.qc.ca
c
c
      subroutine zone_diffusion(
     +effet,cloudbase,zondif,ncell,nvol,stepdi,siz)
       implicit none
       integer i,j,k
       integer ncell,neffet,imin,imax,jmin,jmax,kmax,nvol
       integer keep,stepdi
       real x1,y1,z1,x0,y0,z0
       real effet,dmin,d
       real zondif(3000000,3),siz
       real pi,cloudbase
       pi=3.1415926
       keep=0
       x1=0.
       y1=0.
       z1=0.
       neffet=nint(effet/siz)
       dmin=effet
       stepdi=1
c limits of the calculations loops
       imin=-neffet
       imax=+neffet
       jmin=-neffet
       jmax=+neffet
       kmax=neffet
       ncell=0
       nvol=0
       do i=imin,imax
         x0=real(i)*siz
         do j=jmin,jmax
           y0=real(j)*siz
           do k=1,kmax                                                     
             z0=real(k)*siz-siz/2.
             d=sqrt((x1-x0)**2.+(y1-y0)**2.+(z1-z0)**2.)
             if ((z0.lt.35000.).and.(z0.lt.cloudbase)) then
               if (d.le.dmin) then
                 keep=keep+1
                 nvol=nvol+1
                 if (keep.eq.stepdi) then
                   keep=0
                   ncell=ncell+1
                   zondif(ncell,1)=x0                                   
                   zondif(ncell,2)=y0 
                   zondif(ncell,3)=z0
                 endif
               endif
             endif                                                           ! fin condition au-dessus du sol
           enddo
         enddo
       enddo
       return
       end 
