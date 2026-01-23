C     Last change:  HLS  26 Sep 2003    9:26 am
      SUBROUTINE primv
C   ******************************************************************
C   *                                                                *
C   *    Obtain primitive translational vectors of real space and    *
C   *    read atomic positions (basis).                              *
C   *                                                                *
C   *   *On entry:                                                   *
C   *                                                                *
C   *    LAT   : Lattice according to the list in MESH.              *
C   *                                                                *
C   *   *Input:                                                      *
C   *                                                                *
C   *    A     : Lattice parameter a.                                *
C   *    ALPHA : Crystallographic angle between a and b.             *
C   *    B     : Lattice parameter b.                                *
C   *    BETA  : Crystallographic angle between b and c.             *
C   *    C     : Lattice parameter c.                                *
C   *    GAMMA : Crystallographic angle between c and a.             *
C   *    IPRIM := 0: Read non-standard vectors.                      *
C   *           = 1: Generate standard vectors.                      *
C   *           = 2: Generate supercell.                             *
C   *    NQR2  . Repeat for 2D supercell.                            *
C   *    NQ3   : Number of atoms in the 3D cell.                     *
C   *    QX3                                                         *
C   *    QY3   : Position of atoms in the 3D cell.                   *
C   *    QZ3                                                         *
C   *                                                                *
C   *   *On exit:                                                    *
C   *                                                                *
C   *    BOA   : b/a.                                                *
C   *    BSX(I)                                                      *
C   *    BSY(I): Three primitive translation vectors.                *
C   *    BSZ(I)                                                      *
C   *    COA   : c/a.                                                *
C   *                                                                *
C   ******************************************************************
      USE basis           ; USE control_data    ; USE control_input
      USE csts            ; USE lattice         ; USE message
      IMPLICIT NONE
      CHARACTER(LEN=6) :: SubName=' Primv'
      REAL(KIND=8) :: a, b, c, aa, ba, ca, alpha, beta, gamma, radf
      INTEGER :: iprim, i, nqr2, k, j, iq, irec
  101 FORMAT('Standard choice not implemented for LAT =',i3)
  102 FORMAT(3(10x,f10.6))
  103 FORMAT(/,11x,'A     =',f10.6,' B     =',f10.6,' C     =',f10.6)
  105 FORMAT(11X,'(',F10.5,',',F10.5,',',F10.5,' )')
  106 FORMAT(/,11X,'Primitive vectors for ',A,' lattice in',/,11X,
     1       'units of the lattice spacing a:',/)
  107 FORMAT(/,11X,'A     =',F10.6,' B     =',F10.6,' C     =',F10.6,
     1       /,11X,'Alpha =',F10.3,' Beta  =',F10.3,' Gamma =',F10.3)
  108 FORMAT(/,11X,'Basis vectors:',12X,'NQ3 =',I4,/)
  110 FORMAT('Number of supercell basis vectors must',
     1       ' be equal to ',a,' =',i3)
  111 FORMAT('Supercell calculation: ',a,i3)
  112 FORMAT('Must be smaller than or equal to',a,i3)
C
      IF(msgl > 0) THEN
         WRITE(msgio,'(2a)') SubName,': Construct lattice'
      ENDIF
C
C     Get the crystal stucture data
C
      CALL scnline('NQ3...=',SubName,irec)
      READ(cdata(irec),'(7x,i3,4(8x,i2),6x,i4)') nq3,lat,iprim,nghbp,
     &                                     nqr2,mriq
      IF(mriq==0) THEN
         mriq=100
      ENDIF
C
      IF(nghbp < 1) THEN
         WRITE(errmsg(1),
     &   "(11x,'Number of repeats NGHBP must be positive.')")
         CALL pstop(SubName,1,'Y')
      ENDIF
C
      ALLOCATE(qx3(nq3),qy3(nq3),qz3(nq3))
C
      irec=irec+1
      IF(cdata(irec)(1:3)/='A..') THEN
         WRITE(errmsg(1),'(a)') TRIM(cdata(irec))
         WRITE(errmsg(2),'(a)') 'cdata(1:3) should be A..'
         CALL pstop(SubName,2,'N')
      ENDIF
      READ(cdata(irec),102) a,b,c
      boa=b/a
      coa=c/a
      radf=pi/180.d0
      SELECT CASE (iprim)
      CASE(0)
         WRITE(m6,'(/,4a)') SubName,':    Special choice of',
     &   ' primitive vectors, lattice=',TRIM(tlat(lat))
C
C        Read the primitive vectors on FOR005
C
         DO i=1,3
            irec=irec+1
cc            IF(cdata(irec)(1:3)/='BSX') THEN
cc               WRITE(errmsg(1),'(a)') TRIM(cdata(irec))
cc               WRITE(errmsg(2),'(a)') 'cdata(1:3) should be BSX'
cc               CALL pstop(SubName,2,'N')
cc            ENDIF
            READ(cdata(irec),*) bsx(i),bsy(i),bsz(i)
         ENDDO
         IF(lat==7.AND.bsz(1) < 1.d-07) boa=-1.d0
C
      CASE(1)
         WRITE(m6,'(/,4a)') SubName,':    Default choice of',
     &   ' primitive vectors, lattice=',TRIM(tlat(lat))
C
C        Construct primitive vectors from A,B,C,ALPHA,BETA,GAMMA
C
         IREC=IREC+1
         IF(cdata(irec)(1:3)/='Alp') THEN
            WRITE(errmsg(1),'(a)') TRIM(cdata(irec))
            WRITE(errmsg(2),'(a)') 'cdata(1:3) should be Alp'
            CALL pstop(SubName,2,'N')
         ENDIF
         READ(CDATA(IREC),102) ALPHA,BETA,GAMMA
         ALF=ALPHA*RADF
         BET=BETA*RADF
         GAM=GAMMA*RADF
C
         SELECT CASE(LAT)
         CASE(1)
C
C           Simple cubic
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=0.D0
            BSY(2)=1.D0
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=1.D0
         CASE(2)
C
C           Face centred cubic
C
            BSX(1)=0.5D0
            BSY(1)=0.5D0
            BSZ(1)=0.0D0
            BSX(2)=0.0D0
            BSY(2)=0.5D0
            BSZ(2)=0.5D0
            BSX(3)=0.5D0
            BSY(3)=0.0D0
            BSZ(3)=0.5D0
         CASE(3)
C
C           Body centred cubic
C
            BSX(1)=0.5D0
            BSY(1)=0.5D0
            BSZ(1)=-0.5D0
            BSX(2)=-0.5D0
            BSY(2)=0.5D0
            BSZ(2)=0.5D0
            BSX(3)=0.5D0
            BSY(3)=-0.5D0
            BSZ(3)=0.5D0
         CASE(4)
C
C           Hexagonal
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=-0.5D0
            BSY(2)=SQRT(3.D0)/2.D0
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=COA
         CASE(5)
C
C           Simple tetragonal
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=0.D0
            BSY(2)=1.D0
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=COA
         CASE(6)
C
C           Body centred tetragonal
C
            BSX(1)=1.0D0
            BSY(1)=0.0D0
            BSZ(1)=0.0D0
            BSX(2)=0.0D0
            BSY(2)=1.0D0
            BSZ(2)=0.0D0
            BSX(3)=0.5D0
            BSY(3)=0.5D0
            BSZ(3)=COA/2.D0
         CASE(7)
C
C           Trigonal
C
            BSX(1)=0.D0
            BSY(1)=1.D0
            BSZ(1)=COA
            BSX(2)=-SQRT(3.D0)/2.D0
            BSY(2)=-0.5D0
            BSZ(2)=COA
            BSX(3)=SQRT(3.D0)/2.D0
            BSY(3)=-0.5D0
            BSZ(3)=COA
         CASE(8)
C
C           Simple orthorombic
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=0.D0
            BSY(2)=BOA
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=COA
         CASE(9)
C
C           Base centered orthorombic
C
            BSX(1)=1.D0/2.D0
            BSY(1)=-BOA/2.D0
            BSZ(1)=0.D0
            BSX(2)=1.D0/2.D0
            BSY(2)=BOA/2.D0
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=COA
         CASE(10)
C
C           Body centred orthorombic
C
            BSX(1)=1.D0/2.D0
            BSY(1)=-BOA/2.D0
            BSZ(1)=COA/2.D0
            BSX(2)=1.D0/2.D0
            BSY(2)=BOA/2.D0
            BSZ(2)=-COA/2.D0
            BSX(3)=-1.D0/2.D0
            BSY(3)=BOA/2.D0
            BSZ(3)=COA/2.D0
         CASE(11)
C
C           Face centred orthorombic
C
            BSX(1)=1.D0/2.D0
            BSY(1)=0.D0
            BSZ(1)=COA/2.D0
            BSX(2)=1.D0/2.D0
            BSY(2)=BOA/2.D0
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=BOA/2.D0
            BSZ(3)=COA/2.D0
         CASE(12)
C
C           Simple monoclinic
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=BOA*COS(GAM)
            BSY(2)=BOA*SIN(GAM)
            BSZ(2)=0.D0
            BSX(3)=0.D0
            BSY(3)=0.D0
            BSZ(3)=COA
         CASE(13)
C
C           Base centred monoclinic
C
            BSX(1)=0.D0
            BSY(1)=-BOA
            BSZ(1)=0.D0
            BSX(2)=0.5D0*SIN(GAM)
            BSY(2)=-0.5D0*COS(GAM)
            BSZ(2)=-0.5D0*COA
            BSX(3)=0.5D0*SIN(GAM)
            BSY(3)=-0.5D0*COS(GAM)
            BSZ(3)=0.5D0*COA
         CASE(14)
C
C           Simple triclinic
C
            BSX(1)=1.D0
            BSY(1)=0.D0
            BSZ(1)=0.D0
            BSX(2)=BOA*COS(GAM)
            BSY(2)=BOA*SIN(GAM)
            BSZ(2)=0.D0
            BSX(3)=COA*COS(BET)
            BSY(3)=COA*(COS(ALF)-COS(BET)*COS(GAM))/SIN(GAM)
            BSZ(3)=COA*SQRT((1.D0-COS(GAM)*COS(GAM)-COS(ALF)
     &            *COS(ALF)-COS(BET)*COS(BET)
     &            +2.D0*COS(ALF)*COS(BET)*COS(GAM)))/SIN(GAM)
         CASE DEFAULT
            WRITE(errmsg(1),101) LAT
            CALL pstop(SubName,1,'Y')
         END SELECT
      CASE(2)
         WRITE(m6,'(/,3a)') SubName,':    Supercell',
     &                          ' primitive vectors.'
         WRITE(m6,103) A,B,C
C
C        Read the primitive vectors on FOR005
C
         DO I=1,3
            IREC=IREC+1
            READ(CDATA(IREC),102) BSX(I),BSY(I),BSZ(I)
         ENDDO
         K=0
         DO J=1,NQR2
            DO I=1,NQR2
               K=K+1
               IF(K > NQ3) THEN
                  WRITE(errmsg(1),111) 'K =',K
                  WRITE(errmsg(2),112) 'NQ3 =',NQ3
                  CALL pstop(SubName,2,'Y')
               ENDIF
               QX3(K)=(I-1)*BSX(1)+(J-1)*BSX(2)
               QY3(K)=(I-1)*BSY(1)+(J-1)*BSY(2)
               QZ3(K)=(I-1)*BSZ(1)+(J-1)*BSZ(2)
            ENDDO
         ENDDO
         IF(K /= NQ3) THEN
            WRITE(errmsg(1),110) 'NQ3',NQ3
            CALL pstop(SubName,1,'Y')
         ENDIF
         DO I=1,2
            BSX(I)=NQR2*BSX(I)
            BSY(I)=NQR2*BSY(I)
         ENDDO
      CASE DEFAULT
         WRITE(errmsg(1),"('IPRIM =',I3,'. Must be 0, 1, or 2.')")
     &   iprim
         CALL pstop(SubName,1,'Y')
      END SELECT
C
      AA=SQRT(BSX(1)*BSX(1)+BSY(1)*BSY(1)+BSZ(1)*BSZ(1))
      BA=SQRT(BSX(2)*BSX(2)+BSY(2)*BSY(2)+BSZ(2)*BSZ(2))
      CA=SQRT(BSX(3)*BSX(3)+BSY(3)*BSY(3)+BSZ(3)*BSZ(3))
      ALPHA=ACOS((BSX(2)*BSX(3)+BSY(2)*BSY(3)+BSZ(2)*BSZ(3))/BA/CA)
      BETA=ACOS((BSX(1)*BSX(3)+BSY(1)*BSY(3)+BSZ(1)*BSZ(3))/AA/CA)
      GAMMA=ACOS((BSX(1)*BSX(2)+BSY(1)*BSY(2)+BSZ(1)*BSZ(2))/AA/BA)
      ALPHA=ALPHA/RADF
      BETA=BETA/RADF
      GAMMA=GAMMA/RADF
C
      WRITE(M6,107) A,B,C,ALPHA,BETA,GAMMA
C
C     Read the NQ3 basis vectors in the primitive cell and
C     use the first site as the origin
C
      IF(iprim /= 2) THEN
         DO IQ=1,NQ3
            IREC=IREC+1
cc            IF(cdata(irec)(1:2)/='QX') THEN
cc               WRITE(errmsg(1),'(a)') TRIM(cdata(irec))
cc               WRITE(errmsg(2),'(a)') 'cdata(1:2) should be QX'
cc               CALL pstop(SubName,2,'N')
cc            ENDIF
            READ(CDATA(IREC),*) QX3(IQ),QY3(IQ),QZ3(IQ)
         ENDDO
         QX3(1:NQ3)=QX3(1:NQ3)-QX3(1)
         QY3(1:NQ3)=QY3(1:NQ3)-QY3(1)
         QZ3(1:NQ3)=QZ3(1:NQ3)-QZ3(1)
      ENDIF
C
C     Print primitive and basis vectors
C
      IF(lat >= 1.AND.lat <= 14) THEN
         WRITE(m6,106) tlat(lat)
      ELSE
         WRITE(m6,106) ' unspecified'
      ENDIF
      DO I=1,3
         WRITE(m6,105) BSX(I),BSY(I),BSZ(I)
      ENDDO
      WRITE(m6,108) NQ3
      DO I=1,NQ3
         WRITE(m6,105) QX3(I),QY3(I),QZ3(I)
      ENDDO
C
      RETURN
      END
