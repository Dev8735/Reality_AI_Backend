"""Geospatial query service — radius and boundary search on listings."""

from sqlalchemy.orm import Session
from sqlalchemy import cast, func
from geoalchemy2 import Geometry, Geography
from geoalchemy2.elements import WKTElement

from app.models.listing import Listing


def search_by_radius(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float,
    limit: int = 20,
) -> list[Listing]:
    """Return listings within *radius_km* of the given point.

    Parameters
    ----------
    lat : float
        Latitude, must be in ``[-90, 90]``.
    lng : float
        Longitude, must be in ``[-180, 180]``.
    radius_km : float
        Search radius in kilometres, capped at 100 km to prevent
        accidentally huge queries that would scan the entire table.
    limit : int
        Maximum results to return.

    Notes
    -----
    Both sides of the distance comparison are cast to ``::geography``
    so that the radius (converted to metres) is interpreted as an
    actual surface distance, **not** in degrees.  This is a common
    correctness bug — without the cast, 1 degree ≈ 111 km at the
    equator but much less at higher latitudes.  Do not "simplify" this
    by removing the cast.

    A spatial GiST index on ``listing.location`` (added in Phase 5)
    will make this query fast on large datasets.
    """
    if not (-90 <= lat <= 90):
        raise ValueError(f"lat must be in [-90, 90], got {lat}")
    if not (-180 <= lng <= 180):
        raise ValueError(f"lng must be in [-180, 180], got {lng}")
    if radius_km <= 0:
        raise ValueError(f"radius_km must be positive, got {radius_km}")
    # Cap at 100 km — prevents an accidentally huge query
    radius_km = min(radius_km, 100.0)

    point = WKTElement(f"POINT({lng} {lat})", srid=4326)
    radius_m = radius_km * 1000

    return (
        db.query(Listing)
        .filter(
            func.ST_DWithin(
                cast(Listing.location, Geography),
                cast(point, Geography),
                radius_m,
            )
        )
        .order_by(
            func.ST_Distance(
                cast(Listing.location, Geography),
                cast(point, Geography),
            )
        )
        .limit(limit)
        .all()
    )


def search_by_boundary(
    db: Session,
    polygon: list[list[float]],
    limit: int = 50,
) -> list[Listing]:
    """Return listings situated inside a drawn polygon boundary.

    Parameters
    ----------
    db : Session
        Active database session.
    polygon : list[list[float]]
        List of ``[lat, lng]`` vertices forming a closed ring.
    limit : int
        Max results to return.

    Raises
    ------
    ValueError
        If the shape is self-intersecting or invalid per Shapely.

    Notes
    -----
    WKT standard uses ``(longitude, latitude)`` coordinate ordering!
    We convert the input ``[lat, lng]`` points to ``(lng, lat)`` pairs
    when rendering the WKT string for PostGIS ``ST_GeomFromText``.
    """
    from shapely.geometry import Polygon as ShapelyPolygon

    # Convert [lat, lng] to (lng, lat) for Shapely and WKT
    coords = [(pt[1], pt[0]) for pt in polygon]

    # Validate shape geometry using Shapely
    shape = ShapelyPolygon(coords)
    if not shape.is_valid:
        raise ValueError(
            "Invalid or self-intersecting polygon shape provided"
        )

    # Build WKT POLYGON string: POLYGON((lng lat, lng lat, ...))
    wkt_pts = ", ".join(f"{lng} {lat}" for lng, lat in coords)
    wkt_poly = f"POLYGON(({wkt_pts}))"

    poly_geom = WKTElement(wkt_poly, srid=4326)

    return (
        db.query(Listing)
        .filter(
            func.ST_Contains(
                poly_geom,
                Listing.location,
            )
        )
        .limit(limit)
        .all()
    )

