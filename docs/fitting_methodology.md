# Fitting methodology

The measured signal is modelled as a background plus user-proposed, area-normalised
components. Optimisation is staged through areas, centres, widths, and optionally
mixing fractions. Bounds and exact relationships encode physical and chemical prior
knowledge. Seeded multistart runs probe sensitivity to initial values. Candidate
models are compared with information criteria, residual structure, warnings, and
parameter stability; none of these establishes an assignment without chemical review.

Linear and iterative Shirley backgrounds are implemented. The fitting line shapes
are Gaussian, Lorentzian, and pseudo-Voigt with FWHM semantics. A true Voigt is
available as a primitive. Noise weights are not inferred, so reduced chi-square is
only a residual-per-degree-of-freedom quantity unless intensities have been supplied
with appropriate weighting. Tougaard, asymmetric Kherve LA/GL compatibility, blind
peak discovery, and final publication styling are not part of Phase 1.
