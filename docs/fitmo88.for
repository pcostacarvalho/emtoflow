C     Last change:  IAA  29 Feb 2000   11:00 am
      SUBROUTINE FITMO88(Etot0,Rws0,Bmod,Grun,Etot,Rws,Iuse,NPTF)
C***********************************************************************
C                                                                      *
C                        I.A. Abrikosov                                *
C                                                                      *
C                  Condensed Matter Theory Group,                      *
C           Fysiska Institutionen, Department of Physics               *
C                 Box 530, S-75121 UPPSALA, Sweden                     *
C                                                                      *
C      Calculate parameters of the equation_of_state from              *
C      results of total energy vs Wigner-Seitz radius calculations     *
C      obtained from firs-principles fitted by modified Morse          *
C      function (V.L.Morruzi et. al. Phys.Rev.B, 37, 790-799 (1988).   *
C                                                                      *
C      INPUT:                                                          *
C                                                                      *
C      Etot(1:NPTF)   : first-principles total energies calculated at  *
C      Rws(1:NPTF)    : these Wigner-Seitz radii                       *
C      NPTF           : total number of Wigner-Seitz radii used        *
C                       in first-principles calculations               *
C      Rws0 , Etot0,  : ground state parameters calculated by spline.  *
C      Bmod, Grun                                                      *
C                                                                      *
C      NAG Library subroutine E04FDF is employed.                      *
C                                                                      *
C***********************************************************************
      USE control_data
      USE fit_mo88
      USE for_lsfin1
      IMPLICIT NONE
C     .. Parameters ..
      CHARACTER(LEN=7), PARAMETER :: SRNAME = "FITMO88"
      INTEGER, PARAMETER ::          Ntry = 200
      INTEGER, PARAMETER ::          LIW_parameter = 1
C     .. Scalar arguments ..
      REAL(KIND=8), INTENT (IN) :: Etot0, Rws0, Bmod, Grun
      INTEGER, INTENT (IN) :: NPTF
C     .. Array arguments  ..
      REAL(KIND=8), DIMENSION(*), INTENT (IN) :: Rws, Etot
      INTEGER, DIMENSION(*), INTENT (IN) :: Iuse
C     .. Local scalars ..
      REAL(KIND=8) :: FSUMSQ = 1D9
      REAL(KIND=8) :: alr0, x0, EtotI, R_eq, Bprime, RwsI, VOL, E_eq
      INTEGER :: Npar, LW, NPTFU, NPTFU_here, I, IFAIL, ICALL
      INTEGER :: LIW = LIW_parameter
C     .. Local arrays  ..
      REAL(KIND=8), DIMENSION(:), ALLOCATABLE :: WORK1
      INTEGER,  DIMENSION(LIW_parameter) :: IW
C     .. External Subroutines ..
      EXTERNAL E04FDF    ! E04FDF uses LSFUN1, that is a designated name
      EXTERNAL GSMO88 
C
C     .. Executable Statements ..
C
C       Allocate local arrays
C
      NPTFU = SUM(Iuse(1:NPTF))   !   Iuse_for_fitting = 1 or 0 
      ALLOCATE(Rws_or_Vol(NPTFU), Euse(NPTFU))
      Npar=Npar_mo88
      LW=7*Npar+Npar*Npar+2*Npar*NPTFU+3*NPTFU+Npar*(Npar-1)/2
      ALLOCATE(WORK1(LW))
C
C     Set initial guesses, use array Ymo88 for Moruzzi parameters:
C
C     Ymo88(1)=a
C     Ymo88(2)=b
C     Ymo88(3)=c
C     Ymo88(4)=lambda
C
      Fit_by=1
      Ymo88(4)=2.D0*Grun/Rws0    ! Low-temperature Grun. 
      alr0=-Ymo88(4)*Rws0
      x0=exp(alr0)
      Ymo88(3)=-Bmod/pkbar*6.d0*Pi*alr0/(x0**2*Ymo88(4)**3)
      Ymo88(2)=-2.d0*x0*Ymo88(3)
      Ymo88(1)=-Ymo88(2)*x0-Ymo88(3)*x0*x0
C
C     Choose points to be used for the fitting
C
      NPTFU_here=0
      DO I=1,NPTF
         IF(Iuse(I) == 1) THEN
             NPTFU_here=NPTFU_here + 1
             IF(NPTFU_here > NPTFU) THEN
               WRITE(mout_file,9999) SRNAME, NPTFU_here 
               STOP
             ENDIF
             Rws_or_Vol(NPTFU_here)=Rws(I)
             Euse(NPTFU_here)=Etot(I)
         ENDIF
      END DO
      IF(NPTFU_here /= NPTFU) THEN
         WRITE(mout_file,9999) SRNAME, NPTFU_here 
         STOP
      ENDIF
C
C     Calculate parameters of modified Morse function
C
      DO ICALL = 1, Ntry
         IFAIL = 1
         CALL E04FDF(NPTFU,Npar,Ymo88,FSUMSQ,IW,LIW,WORK1,LW,IFAIL)
      IF(IFAIL == 0) EXIT
      END DO
C
C     Output
C
C     Print initial and fitted values, rms
C
      WRITE(mout_file,9997) Input_R_or_V
      DO I=1,NPTF
         CALL GSMO88(Ymo88,Rws(I),EtotI,'Print')
         EtotI=Etot(I)+zero_energy
         CALL TRNSFM(Rws(I),E_at_V,EtotI,RwsI,VOL,E_at_V,EtotI)
         IF(Transform_to_V == 'Y') RwsI = VOL
         WRITE(mout_file,9996) RwsI,EtotI,E_at_V,P_at_V,Iuse(I)
         IF(I == 1) THEN
           Prs_max = P_at_V
           Vol_left=Pi43*RwsI*RwsI*RwsI
         ELSE IF(I == NPTF) THEN
           Prs_min = P_at_V
           Vol_right=Pi43*RwsI*RwsI*RwsI
         ENDIF
      END DO
      WRITE(mout_file,9995) SRNAME, fsumsq, IFAIL, ICALL-1
C
C     Calculate and print ground state parameters
C
      CALL GSMO88(Ymo88,R_eq,EtotI,'Ground_state')
      Bprime=2.d0*(Grun_at_V+1.d0)
      CALL TRNSFM(R_eq,E_at_V,EtotI,RwsI,VOL,E_eq,EtotI)
      WRITE(mout_file,9994) RwsI, R_or_V_units, VOL,
     &                      R_or_V_units//'^3', E_eq, Energy_units,
     &                      B_at_V, Bprime, Grun_at_V
      WRITE(mout_file,9992) Ymo88(1:Npar_mo88)
C
C     See if the ground state parameters agree with those   
C     obtained by the spline interpolation
C
        IF(ABS((R_eq-Rws0)/Rws0) > 0.1 ) THEN
          WRITE(mout_file,9993) SRNAME, 'Wigner-Seitz', R_eq, Rws0
        ENDIF
        IF(ABS(E_at_V-Etot0) > 0.01 ) THEN
          WRITE(mout_file,9993) SRNAME, 'total energy', E_at_V, Etot0
        ENDIF
        IF(ABS((B_at_V-Bmod)/Bmod) > 0.2 ) THEN
          WRITE(mout_file,9993) SRNAME, 'bulk modulus', B_at_V, Bmod
        ENDIF
        IF(ABS((Grun_at_V-Grun)/Grun) > 0.2 ) THEN
          WRITE(mout_file,9993) SRNAME, 'Gruneisen constant', Grun_at_V, 
     &                          Grun
        ENDIF
C
C     Deallocate arrays
C
      DEALLOCATE(Rws_or_Vol, Euse, WORK1)
C
C     .. Formats ..
C
 9999 format(/,1X,A,': Number of points to use for the fitting ',
     1       I4,/,10X,'does not agree with data file specifications.',
     2       /,10X,'Use 1 (0) to include (exclude) points into fitting')
 9998 format(/,1X,A,': ',A,' has returned IFAIL =',I4)
 9997 format(/,5X,A,11X,'Etot',13X,'Efit',12X,'Prs',10X,'Set')
 9996 format(1X,F10.5,2(1X,F16.8),1X,F12.5,5X,I3)
 9995 format(/,1X,A,': ',5('*'),' fsumsq=',E15.10,', IFAIL =',I3,
     1       ', ICALL =',I4)
 9994 format(/,10X,'Ground state parameters:',//,
     1         10X,'Rwseq    =',F18.10,A,/,
     2         10X,'V_eq     =',F18.10,A,/,
     3         10X,'Eeq      =',F18.10,A,/,
     4         10X,'Bmod     =',F18.10,' kBar',/,
     5         10X,'B''       =',F18.10,/,
     6         10X,'Gamma    =',F18.10)
 9993 format(/,1X,A,': Calculated ',A,' is quite different from one',/,
     1       10X,'obtained by polinomial fit!!!',/,10X,
     2      'Obtained value is ',F18.10,/,10X,'Polinoms gave      ',
     3      F18.10,/,10X,'This could indicate a pecularity ',
     4      'at the binding energy curve.')
 9992 format(/,10X,' Morse curve parameters:',/,
     1         10X,' a        =',F18.10,/,
     2         10X,' b        =',F18.10,/,
     3         10X,' c        =',F18.10,/,
     4         10X,' lambda   =',F18.10)
      RETURN
      END SUBROUTINE FITMO88

      SUBROUTINE GSMO88(Ymo88,Rws,E_at_R,MODE_EQ)
C***********************************************************************
C                                                                      *
C      Calculate E_at_R for a Wigner-Sietz radius Rws using            *
C      modified Morse function by V.L.Morruzi et. al. (Default case)   *
C                                                                      *
C      Calculate ground state parameters E_at_V, P_at_V, B_at_V,       *
C      and Grun_at_V for this volume.                                  *
C                                                                      *
C      The ground state parameters are in the module control_data.     *
C                                                                      *
C      The equilibrium parameters are calculated if MODE_EQ = 'G'      *
C                                                                      *
C***********************************************************************
      USE control_data
      IMPLICIT NONE
C     .. Parameters ..
      INTEGER, PARAMETER :: Npar_mo88 = 4
C     .. Scalar arguments ..
      CHARACTER(*), INTENT (IN) :: MODE_EQ
      REAL(KIND=8), INTENT (IN OUT) :: Rws
      REAL(KIND=8), INTENT (OUT) :: E_at_R
C     .. Array arguments ..
      REAL(KIND=8), DIMENSION(Npar_mo88), INTENT (IN) :: Ymo88
C     .. Local scalars ..
      REAL(KIND=8) :: x, alx, twocx, x0, alx0
C
C     .. Executable Statements ..
C
      SELECT CASE (MODE_EQ(1:1))
      CASE('G', 'g')
C
C     Calculate equilibrium parameters
C
         x0=-Ymo88(2)/(2.d0*Ymo88(3))
         alx0=log(x0)
         Rws=-alx0/Ymo88(4)
         B_at_V=-Ymo88(3)*x0*x0*Ymo88(4)**3/(6.d0*Pi*alx0)*pkbar
         Grun_at_V=Ymo88(4)*Rws/2.D0   ! Low-temperature Grun.
         E_at_R=Ymo88(1)+Ymo88(2)*x0+Ymo88(3)*x0*x0
         E_at_V=E_at_R+zero_energy
         P_at_V=0.D0
      CASE('P', 'p')
C
C     Calculate all the parameters for a particular Rws
C
       alx=-Ymo88(4)*Rws
       x=exp(alx)
       twocx=2.d0*Ymo88(3)*x
       E_at_R=Ymo88(1)+Ymo88(2)*x+Ymo88(3)*x*x
       E_at_V=E_at_R+zero_energy
       P_at_V=x*Ymo88(4)**3*(Ymo88(2)+twocx)/(4.d0*Pi*alx*alx)*pkbar
       B_at_V=-(x*Ymo88(4)**3)/(12.d0*Pi*alx)*((Ymo88(2)+2.d0*twocx)-
     -        2.d0/alx*(Ymo88(2)+twocx))*pkbar
C
C     So far I have neglected volume dependence of Gruniesen
C     parameter. One just need to take corresponding derivatives
C     (see Appendix of Moruzzi'88 paper)
C
         x0=-Ymo88(2)/(2.d0*Ymo88(3))
         alx0=log(x0)
C
       Grun_at_V=Ymo88(4)*(-alx0/Ymo88(4))/2.D0  ! Low temperature Grun
      CASE DEFAULT
C
C     Calculate total energy for a particular Rws
C     Zero energy is subtructed.
C
       x=exp(-Ymo88(4)*Rws)
       E_at_R=Ymo88(1)+Ymo88(2)*x+Ymo88(3)*x*x
      END SELECT
      RETURN
      END SUBROUTINE GSMO88

      SUBROUTINE HMO88(VOL,Enthalpy,dHdV)
C***********************************************************************
C                                                                      *
C      Calculate the Enthalpy and its first volume derivative dHdV     *
C      at a volume VOL by modified Morse function after V.L.Morruzi    *
C      et. al. parameters have been determined in the calling routine. *
C                                                                      *
C***********************************************************************
      USE control_data
      USE fit_mo88
      IMPLICIT NONE
C     .. Scalar arguments ..
      REAL(KIND=8), INTENT (OUT) :: Enthalpy, dHdV
      REAL(KIND=8), INTENT (IN) :: VOL
C     .. Local scalars ..
      REAL(KIND=8) :: Rws, E_at_R, P_ext
C     .. External subroutine ..
      EXTERNAL GSMO88
C
C     .. Executable Statements ..
C
      P_ext = P_ext_kbar/pkbar
      Rws   = (VOL/Pi43)**0.33333333333333333333d0
      CALL GSMO88(Ymo88,Rws,E_at_R,'Print')
      Enthalpy = E_at_V + P_ext * VOL
      dHdV   = -P_at_V/pkbar + P_ext
      RETURN
      END SUBROUTINE HMO88
