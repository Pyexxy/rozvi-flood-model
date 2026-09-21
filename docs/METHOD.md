# Method note

## Susceptibility score

Each driver is scaled to the interval [1, 10] using the 2nd and 98th percentiles of values inside the analysis bounding box. Elevation, slope and water-distance (or height above local minima) are inverted so that higher physical values correspond to lower susceptibility. Missing pixels receive a neutral value of 5 before weighting.

The composite score is the weighted sum of the scaled drivers. Weights are defined in `config/default.yaml` and must sum to 1.

## Risk category

```
category = round((score - 1) / 9 * 100)
```

Bands follow the ranges documented in the main README.

## Chainage

Chainage is measured along each parent line feature from its first vertex after projection to a local metric CRS. It is a model coordinate system, not an official road-authority chainage, until replaced with surveyed alignment data.

## Screening threshold

Segments with susceptibility score greater than or equal to 7 are counted as meeting the screening exposure threshold in summary tables. This threshold is a project convention for prioritisation, not a calibrated probability of flooding.
