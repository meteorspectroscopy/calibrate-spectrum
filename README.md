# calibrate-spectrum
calibration of meteor spectra with laser or spectral lamp

Introduction

I have described a method for the analysis of meteor spectra from video images with a Python script using a GUI here: https://github.com/meteorspectroscopy/meteor-spectrum . In order to apply this method, the camera – lens – grating system has to be calibrated. This is necessary, because the spectra of meteors are nonlinear in a double sense. For meteors illuminating the grating at an angle to the plane perpendicular to the grating lines, the spectra show a hyperbolic curvature. In addition, the dispersion or scale of the spectrum in wavelength units per pixel changes nonlinearly, depending on the incidence angle of the meteor light on the grating. During the flight of the meteor this angle changes, making the simple addition of spectra difficult. These effects are visible in the following spectrum (recorded by Koji Maeda):
 
The idea is to transform the images in such a way, that the nonlinearities in the spectra are removed and do the analysis of the spectra with these transformed images:
 
The details of the method, in particular the transformation of nonlinear spectra to linear spectra with a transformation of the images to an orthographic projection are described here:
https://meteorspectroscopy.files.wordpress.com/2018/01/meteor_spectroscopy_wgn43-4_2015.pdf.
The script presented here allows the determination of the parameters of this transformation from recordings of laser spectra or recordings of spectra of a spectral lamp. 
An aberration free lens produces a gnomonic or tangential projection of the sky on the CCD sensor. Wide angle lenses add some distortion to this image. The desired transformation corrects lens distortion and produces an orthographic or sine projection of the sky. The transformation is axial symmetric about the optical axis, provided that the grating is mounted perpendicularly to this axis. It is characterized by a polynomial in the radial coordinate:
r = r’ * (1 + a3 * r^2 + a5 * r^4 + …). 
r is the radial coordinate in the original image plane, r’ the transformed radial coordinate. This function is used to determine the original coordinate for each pixel in the transformed image in the script m_spec.
It is defined in such a way that in the centre the scale is not changed.  In practice two parameters a3 and a5 are sufficient to describe the radial distortion.  
Starting point for the determination of the parameters of the image transformation is an image with several spectra covering the image area:
 

The script allows the measurement of the coordinates of the spectral lines (different diffraction orders of laser lines (9 spectra with 4 orders each). The spectra are linearized by a least square fit, where the parameters of the transformation are the variables. In addition to the parameters a3 and a5 the coordinates of the optical axis, the dispersion and the rotation of the spectra from the horizontal are also determined. This parameter set is used in the script m_spec for the analysis of meteor spectra.

The script allows going through all the steps:
-	creation of images from short video frames
-	adding spectra to create peak images
-	measuring line positions 
-	least square fit to determine transformation parameters
-	plot of fit results:
 In addition to laser spectra also spectra of spectral lamps can be used for the evaluation of transformation parameters. In this case a list of wavelengths of the lines used for calibration is required, as in the following spectrum of a Hg-Ar spectral lamp:
 
The selected lines are marked with their wavelength. In this case a fairly long focal length was used, which results in a small curvature and nonlinearity of the spectra.

For details on the processing consult the manual M_CALIB_Python_manual.pdf
