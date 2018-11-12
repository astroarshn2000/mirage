#! /usr/bin/env python

"""
Tools for generating Mirage-compatible catalogs from surveys
"""

import astropy.units as u
from astroquery.irsa import Irsa
import numpy as np

from mirage.catalogs.catalog_generator import PointSourceCatalog, GalaxyCatalog


def get_2MASS_ptsrc_catalog(ra, dec, box_width):
    """Query the 2MASS All-Sky Point Source Catalog in a square region around the RA and Dec
    provided. Box width must be in units of arcseconds

    Parameters
    ----------
    something
    """
    # Don't artificially limit how many sources are returned
    Irsa.ROW_LIMIT = 1000000  # -1?

    ra_dec_string = "{}  {}".format(ra, dec)
    query_table = Irsa.query_region(ra_dec_string, catalog='fp_psc', spatial='Box',
                                    width=box_width * u.arcsec)

    # Exclude any entries with missing RA or Dec values
    radec_mask = filter_bad_ra_dec(query_table)
    cat = PointSourceCatalog(ra=query_table['ra'].data.data.data[radec_mask],
                             dec=query_table['dec'].data.data.data[radec_mask])

    # Add the J, H, and K magnitudes as they may be useful for magnitude conversions later
    # Add the values that have had fill_values applied. The fill_value is 1e20.
    for key in ['j_m', 'h_m', 'k_m']:
        data = query_table[key].filled().data
        cat.add_magnitude_column(data, instrument='2MASS', filter_name=key)

    return cat


def twoMASS_plus_background(ra, dec, box_width, kmag_limits=(17, 29), email=''):
    """Convenience function to create a catalog from 2MASS and add a population of
    fainter stars. In this case, cut down the magnitude limits for the call to the
    Besancon model so that we don't end up with a double population of bright stars
    """
    two_mass = get_2MASS_ptsrc_catalog(ra, dec, box_width)
    and then...


def besancon(ra, dec, box_width, coords='ra_dec', email='', kmag_limits=(10, 29)):
    """test it out
    coords keyword can be 'ra_dec', which is default, or
    'galactic' in which case ra and dec are interpreted as galactic longitude and
    latitude

    email is required for the besancon call. kind of annoying.

    """
    from astroquery.besancon import Besancon
    from astropy import units as u
    from astropy.coordinates import SkyCoord

    # Specified coordinates. Will need to convert to galactic long and lat
    # when calling model
    ra = ra * u.deg
    dec = dec * u.deg
    box_width = box_width * u.arcsec

    if coords == 'ra_dec':
        location = SkyCoord(ra=ra, dec=dec, frame='icrs')
        coord1 = location.galactic.l.value
        coord2 = location.galactic.b.value
    elif coords == 'galactic':
        coord1 = ra.value
        coord2 = dec.value

    # Area of region to search (model expects area in square degrees)
    area = box_width * box_width
    area = area.to(u.deg * u.deg)

    # Query the model
    model = Besancon.query(coord1, coord2, smallfield=True, area=area.value,
                           colors_limits={"J-H": (-99, 99), "J-K": (-99, 99),
                                          "J-L": (-99, 99), "V-K": (-99, 99)},
                           mag_limits={'K': kmag_limits}, retrieve_file=True, email=email)

    # Calculate magnitudes in given bands
    k_mags = (model['V'] - model['V-K']).data
    j_mags = k_mags + model['J-K'].data
    h_mags = j_mags - model['J-H'].data
    l_mags = j_mags - model['J-L'].data

    # Since these are theoretical stars generated by a model, we need to provide RA and Dec values.
    # The model is run in 'smallfield' mode, which assumes a constant density of stars across the given
    # area. So let's just select RA and Dec values at random across the fov.
    half_width = box_width * 0.5
    min_ra = ra - half_width
    max_ra = ra + half_width
    min_dec = dec - half_width
    max_dec = dec + half_width
    ra_values, dec_values = generate_ra_dec(len(k_mags), min_ra, max_ra, min_dec, max_dec)

    # Create the catalog object
    cat = PointSourceCatalog(ra=ra_values, dec=dec_values)

    # Add the J, H, K and L magnitudes as they may be useful for magnitude conversions later
    cat.add_magnitude_column(j_mags, instrument='Besancon', filter_name='j')
    cat.add_magnitude_column(h_mags, instrument='Besancon', filter_name='h')
    cat.add_magnitude_column(k_mags, instrument='Besancon', filter_name='k')
    cat.add_magnitude_column(l_mags, instrument='Besancon', filter_name='l')
    return cat


def galactic_plane(box_width, email=''):
    """Convenience function to create a typical scene looking into the disk of
    the Milky Way, using the besancon function

    Parameters
    ----------
    box_width : float

    Returns
    -------
    cat : obj
        mirage.catalogs.create_catalog.PointSourceCatalog

    RA and Dec values of various features

    Center of MW
    center_ra = 17h45.6m
    center_dec = -28.94 deg

    anti-center-ra = 5h45.6m
    anti-center-dec = 28.94deg

    Galactic Poles
    north_pole_ra = 12h51.4m
    north_pole_dec = 27.13deg

    south_pole_ra = 0h51.4m
    south_pole_dec = -27.13deg
    """
    representative_galactic_longitude = 45.0  # deg
    representative_galactic_latitude = 0.0  # deg

    cat = besancon(representative_galactic_longitude, representative_galactic_latitude,
                   box_width, coords='galactic', email=email)
    return cat


def out_of_plane(box_width, email=''):
    """Convenience function to create typical scene looking out of the plane of
    the Milky Way

    Parameters
    ----------
    box_width : float

    Returns
    -------
    cat : obj
        mirage.catalogs.create_catalog.PointSourceCatalog
    """
    representative_galactic_longitude = 45.0  # deg
    representative_galactic_latitude = 85.0  # deg

    cat = besancon(representative_galactic_longitude, representative_galactic_latitude,
                   box_width, coords='galactic', email=email)
    return cat


def galactic_bulge(box_width, email=''):
    """Convenience function to create typical scene looking into bulge of
    the Milky Way

    Parameters
    ----------
    box_width : float

    Returns
    -------
    cat : obj
        mirage.catalogs.create_catalog.PointSourceCatalog
    """
    Look up Besancon limitations. Model breaks down somewhere close to the
    galactic core.
    representative_galactic_longitude = 0.?  # deg
    representative_galactic_latitude = 5.0 ? # deg

    cat = besancon(representative_galactic_longitude, representative_galactic_latitude,
                   box_width, coords='galactic', email=email)
    return cat

#def from_luminosity_function(self, luminosity_function):
#    more customizable


def filter_bad_ra_dec(table_data):
    """Use the column masks to find which entries have bad RA or Dec values.
    These will be excluded from the Mirage catalog

    Parameters
    ----------
    something
    """
    ra_data = table_data['ra'].data.data
    ra_mask = ~table_data['ra'].data.mask
    dec_data = table_data['dec'].data.data
    dec_mask = ~table_data['dec'].data.mask
    position_mask = ra_mask & dec_mask
    return position_mask


def generate_ra_dec(number_of_stars, ra_min, ra_max, dec_min, dec_max):
    """Generate a list of random RA, Dec values"""
    delta_ra = ra_max - ra_min
    ra_list = np.random.random(number_of_stars) * delta_ra + ra_min
    delta_dec = dec_max - dec_min
    dec_list = np.random.random(number_of_stars) * delta_dec + dec_min
    return ra_list, dec_list




