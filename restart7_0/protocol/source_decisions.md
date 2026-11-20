# Evidence for the revision

The release uses cached Restart 6 source records and their existing provenance.
The following official documentation was consulted on 2026-10-28. No new crime
or ATM extracts were downloaded.

- [Illinois State Police LEADS bulletin](https://isp.illinois.gov/LawEnforcement/GetFile/99f66471-ae2a-48b2-a4df-7a781dbc7975)
  maps IUCR 0760 to NIBRS 23F, theft from a motor vehicle. Excluding it aligns
  the working endpoint with structural burglary rather than the local legal name.
- [FBI UCR handbook](https://ucr.fbi.gov/additional-ucr-publications/ucr_handbook.pdf),
  page 33, describes theft from trucks and truck trailers as theft from vehicles.
  This supports excluding NYC's explicit truck-burglary codes. It does not
  independently adjudicate every native case or the remaining codebook.
- [FBI NIBRS 2025 user manual](https://fbibiospecs.fbi.gov/biometric-specifications-1-1/crime-and-law-enforcement-statistics-unit-document-review/nibrs-user-manual-version-2025-0.pdf)
  distinguishes 220 burglary/breaking and entering from 23F theft from vehicles.
- [Chicago dataset](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)
  supplies privacy-protected block locations and update times, not usable original
  report dates for this release. No report dates are inferred from updates.
- [LA NIBRS dataset](https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep)
  describes the March 7, 2024 reporting-system transition and hundred-block
  coordinates. More precise geodesic arithmetic cannot reverse that displacement.

OSM data remain © OpenStreetMap contributors, under the
[ODbL](https://www.openstreetmap.org/copyright), obtained through HeiGIT ohsome.
ACS and EPA source definitions, vintages and geography are inherited from the
[Restart 6 feature methods](../../restart6_0/results/phase3/docs/02_methods.md).
