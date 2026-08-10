# Third-party material in cqrs-bus

cqrs-bus is MIT licensed and its source was written for this project. This file
records anything that came from elsewhere.

## Dependencies

The runtime has none: `dependencies = []`. The published wheel contains this
package and nothing else, so it carries no third-party notice obligation.

Optional and development extras are declared, resolved by the installer and
never vendored into the wheel:

| Package | Extra | License |
| --- | --- | --- |
| prometheus-client | `prometheus` | Apache-2.0 |
| pytest, pytest-asyncio, pytest-cov | dev | MIT |

## Prior art

CQRS, the mediator pattern and the handler registry are architectural ideas with
a long published history (Greg Young, Martin Fowler, and MediatR in .NET, which
the `mediatr` keyword in `pyproject.toml` points at for discovery). Ideas and
API shapes are not protected; no code from MediatR or from any Python package in
the same space was read into this implementation.

## Reviewed and cleared

Nothing yet. Findings from `scripts/provenance-check.py` that turn out to be
convergent output rather than copying belong here, with the date and the
reasoning.
