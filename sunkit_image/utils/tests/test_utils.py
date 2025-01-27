import warnings

import numpy as np
import pytest

import astropy.units as u
from astropy.tests.helper import assert_quantity_allclose

import sunkit_image.utils as utils


@pytest.fixture
@pytest.mark.remote_data
def smap():
    import sunpy.data.sample
    from sunpy.data.sample import AIA_171_IMAGE

    return sunpy.map.Map(AIA_171_IMAGE)


def test_equally_spaced_bins():
    # test the default
    esb = utils.equally_spaced_bins()
    assert esb.shape == (2, 100)
    assert esb[0, 0] == 1.0
    assert esb[1, 0] == 1.01
    assert esb[0, 99] == 1.99
    assert esb[1, 99] == 2.00

    # Bins are 0.015 wide
    esb2 = utils.equally_spaced_bins(inner_value=0.5)
    assert esb2.shape == (2, 100)
    assert esb2[0, 0] == 0.5
    assert esb2[1, 0] == 0.515
    assert esb2[0, 99] == 1.985
    assert esb2[1, 99] == 2.00

    # Bins are 0.2 wide
    esb2 = utils.equally_spaced_bins(outer_value=3.0)
    assert esb2.shape == (2, 100)
    assert esb2[0, 0] == 1.0
    assert esb2[1, 0] == 1.02
    assert esb2[0, 99] == 2.98
    assert esb2[1, 99] == 3.00

    # Bins are 0.01 wide
    esb2 = utils.equally_spaced_bins(nbins=1000)
    assert esb2.shape == (2, 1000)
    assert esb2[0, 0] == 1.0
    assert esb2[1, 0] == 1.001
    assert esb2[0, 999] == 1.999
    assert esb2[1, 999] == 2.000

    # The radii have the correct relative sizes
    with pytest.raises(ValueError):
        utils.equally_spaced_bins(inner_value=1.0, outer_value=1.0)
    with pytest.raises(ValueError):
        utils.equally_spaced_bins(inner_value=1.5, outer_value=1.0)

    # The number of bins is strictly greater than 0
    with pytest.raises(ValueError):
        utils.equally_spaced_bins(nbins=0)


def test_bin_edge_summary():
    esb = utils.equally_spaced_bins()

    center = utils.bin_edge_summary(esb, "center")
    assert center.shape == (100,)
    assert center[0] == 1.005
    assert center[99] == 1.995

    left = utils.bin_edge_summary(esb, "left")
    assert left.shape == (100,)
    assert left[0] == 1.0
    assert left[99] == 1.99

    right = utils.bin_edge_summary(esb, "right")
    assert right.shape == (100,)
    assert right[0] == 1.01
    assert right[99] == 2.0

    # Correct selection of summary type
    with pytest.raises(ValueError):
        utils.bin_edge_summary(esb, "should raise the error")

    # The correct shape of bin edges are passed in
    with pytest.raises(ValueError):
        utils.bin_edge_summary(np.arange(0, 10), "center")
    with pytest.raises(ValueError):
        utils.bin_edge_summary(np.zeros((3, 4)), "center")


@pytest.mark.remote_data
def test_find_pixel_radii(smap):
    # The known maximum radius
    known_maximum_pixel_radius = 1.84183121

    # Calculate the pixel radii
    pixel_radii = utils.find_pixel_radii(smap)

    # The shape of the pixel radii is the same as the input map
    assert pixel_radii.shape[0] == int(smap.dimensions[0].value)
    assert pixel_radii.shape[1] == int(smap.dimensions[1].value)

    # Make sure the unit is solar radii
    assert pixel_radii.unit == u.R_sun

    # Make sure the maximum
    assert_quantity_allclose((np.max(pixel_radii)).value, known_maximum_pixel_radius)

    # Test that the new scale is used
    pixel_radii = utils.find_pixel_radii(smap, scale=2 * smap.rsun_obs)
    assert_quantity_allclose(np.max(pixel_radii).value, known_maximum_pixel_radius / 2)


@pytest.mark.remote_data
def test_get_radial_intensity_summary(smap):
    radial_bin_edges = u.Quantity(utils.equally_spaced_bins(inner_value=1, outer_value=1.5)) * u.R_sun
    summary = np.mean

    map_r = utils.find_pixel_radii(smap, scale=smap.rsun_obs).to(u.R_sun)

    nbins = radial_bin_edges.shape[1]

    lower_edge = [map_r > radial_bin_edges[0, i].to(u.R_sun) for i in range(0, nbins)]
    upper_edge = [map_r < radial_bin_edges[1, i].to(u.R_sun) for i in range(0, nbins)]

    with warnings.catch_warnings():
        # We want to ignore RuntimeWarning: Mean of empty slice
        warnings.simplefilter("ignore", category=RuntimeWarning)
        expected = np.asarray([summary(smap.data[lower_edge[i] * upper_edge[i]]) for i in range(0, nbins)])

    assert np.allclose(utils.get_radial_intensity_summary(smap=smap, radial_bin_edges=radial_bin_edges), expected)
