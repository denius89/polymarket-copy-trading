"""Explicit source dispatch; never label REST rows as RTDS frames."""
import rtds_provenance as rtds
import maker_provenance as maker

q=rtds.q
ProvenanceError=rtds.ProvenanceError


def validator(event):
    receipt=event.get('venueReceipt')
    source=receipt.get('source') if isinstance(receipt,dict) else None
    if source==rtds.SOURCE:return rtds
    if source==maker.SOURCE:return maker
    raise ProvenanceError('POLYMARKET_SOURCE_NOT_ALLOWED')


def validate(event,at_ms):return validator(event).validate(event,at_ms)
def validate_estimate(event,estimate):return validator(event).validate_estimate(event,estimate)
