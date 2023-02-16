! Based on Shapiro 1982 Table 11

MODULE CLOUDS_M

  USE MATH_M, ONLY POLYNOMIAL
  IMPLICIT NONE

CONTAINS

  REAL(8) FUNCTION CLOUD_REFLECTANCE(zenith_angle, cloud_type) RESULT(refl)

    INTEGER(4), INTENT(IN) :: cloud_type
    REAL(8), INTENT(IN) :: zenith_angle

    REAL(8) :: coeffs(4)

    SELECT CASE (cloud_type)
    CASE (1)  ! thin cirrus & cirrostratus
      coeffs = [0.25674D0, -0.18077D0, -0.21961D0, 0.25272D0]
    CASE (2)  ! thick cirrus & cirrostratus
      coeffs = [0.60540D0, -0.55142D0, -0.23389D0, 0.43648D0]
    CASE (3)  ! altostratus & altocumulus
      coeffs = [0.66152D0, -0.14863D0, -0.08193D0, 0.13442D0]
    CASE (4)  ! stratocumulus & stratus
      coeffs = [0.71214D0, -0.15033D0, 0.00696D0, 0.03904D0]
    CASE (5)  ! cumulus & cumulonimbus
      coeffs = [0.67072D0, -0.13805D0, -0.10895D0, 0.09460D0]
    CASE default
      coeffs = [1.0D0, 0.0D0, 0.0D0, 0.0D0]
    END SELECT

    refl = POLYNOMIAL(COS(zenith_angle), coeffs)

  END FUNCTION CLOUD_REFLECTANCE

  REAL(8) FUNCTION CLOUD_TRANSMITTANCE(zenith_angle, cloud_type) RESULT(trans)

    IMPLICIT NONE

    INTEGER(4), INTENT(IN) :: cloud_type
    REAL(8), INTENT(IN) :: zenith_angle

    REAL(8) :: coeffs(4)

    SELECT CASE (cloud_type)
    CASE (1)        ! thin cirrus & cirrostratus
      coeffs = [0.63547D0, 0.35229D0, 0.08709D0, -0.22902D0]
    CASE (2)   ! thick cirrus & cirrostratus
      coeffs = [0.26458D0, 0.66829D0, 0.24228D0, -0.49357D0]
    CASE (3)   ! altostratus & altocumulus
      coeffs = [0.19085D0, 0.32817D0, -0.08613D0, -0.08197D0]
    CASE (4)   ! stratocumulus & stratus
      coeffs = [0.13610D0, 0.29964D0, -0.14041D0, 0.00952D0]
    CASE (5)   ! cumulus & cumulonimbus
      coeffs = [0.17960D0, 0.34855D0, -0.14875D0, 0.01962D0]
    CASE default
      coeffs = [1.0D0, 0.0D0, 0.0D0, 0.0D0]
    END SELECT

    trans = POLYNOMIAL(COS(zenith_angle), coeffs)

  END FUNCTION CLOUD_TRANSMITTANCE

END MODULE CLOUDS_M
