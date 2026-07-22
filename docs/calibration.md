# Binding-energy calibration

For one sample, the rigid correction is

```text
delta_E = E_target - E_reference_fit
```

`E_reference_fit` is the full-precision fitted centre stored in the reviewed C 1s
bundle. A displayed label such as `284.4 eV` is rounded and must not be used for
the calculation. The envelope maximum is also not a substitute for the selected
component centre.

One exact `delta_E` is applied to every region acquired for that sample: C 1s,
N 1s, O 1s, Cl 2p, Survey, and additional regions. Another compound receives its
own independently reviewed correction. The command refuses missing reviewed
regions unless the analyst explicitly allows and records an incomplete scope.

Calibration changes energy arrays, absolute fitted centres, and absolute centre
bounds. It does not change raw intensity, background, component intensity,
total-fit intensity, residual, FWHM, area, uncertainty, or acquisition intensity.
Survey is stored as a reviewed spectrum artifact, never as a fake peak fit.

The reference component must be named explicitly and accompanied by a scientific
rationale. For these PDI samples, the principal carbon component is intrinsic
aromatic carbon rather than an obviously isolated adventitious-carbon peak; the
choice to reference it to 284.8 eV is therefore a scientific judgement that must
be documented, not an automatic largest-peak rule.
