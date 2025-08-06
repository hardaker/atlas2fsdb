"""Convert RIPE Atlas json files to FSDB TSV"""

from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType, Namespace
from logging import debug, info, warning, error, critical
import logging
import sys
import json
import pyfsdb
import dns.message
import base64

# optionally use rich
try:
    from rich import print
    from rich.logging import RichHandler
    from rich.theme import Theme
    from rich.console import Console
except Exception:
    debug("install rich and rich.logging for prettier results")

# optionally use rich_argparse too
help_handler = ArgumentDefaultsHelpFormatter
try:
    from rich_argparse import RichHelpFormatter

    help_handler = RichHelpFormatter
except Exception:
    debug("install rich_argparse for prettier help")


def parse_args() -> Namespace:
    """Parse the command line arguments."""
    parser = ArgumentParser(
        formatter_class=help_handler,
        description=__doc__,
        epilog="Example Usage: atlas2fsdb input.json output.fsdb",
    )

    parser.add_argument(
        "--log-level",
        "--ll",
        default="info",
        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).",
    )

    parser.add_argument(
        "input_file", type=FileType("r"), nargs="?", default=sys.stdin, help=""
    )

    parser.add_argument(
        "output_file", type=FileType("w"), nargs="?", default=sys.stdout, help=""
    )

    args = parser.parse_args()
    log_level = args.log_level.upper()
    handlers = []
    datefmt = None
    messagefmt = "%(levelname)-10s:\t%(message)s"

    # see if we're rich
    try:
        handlers.append(
            RichHandler(
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                console=Console(
                    stderr=True, theme=Theme({"logging.level.success": "green"})
                ),
            )
        )
        datefmt = " "
        messagefmt = "%(message)s"
    except Exception:
        debug("failed to install RichHandler")

    logging.basicConfig(
        level=log_level, format=messagefmt, datefmt=datefmt, handlers=handlers
    )
    return args


def main():
    args = parse_args()
    contents = json.load(args.input_file)

    # a given query contains attributes that apply to
    # a nested list of multiple results
    outer_contents = {
        "probe_id": "prb_id",
        "probe_src": "from",
        "query_type": "type",
        "event_timestamp": "timestamp",
        "stored_timestamp": "stored_timestamp",
    }

    # each nested result has its own parameters
    result_contents = {
        "result_timestamp": "time",
        "dst_addr": "dst_addr",
        "dst_port": "dst_port",
        "address_family": "af",
        "protocol": "proto",
        "src_addr": "src_addr",
    }

    # and inside the result is another "result" structure with greater
    # details
    result_result_contents = {
        "response_time": "rt",
        "size": "size",
        "ancount": "ANCOUNT",
        "qdcount": "QDCOUNT",
        "nscount": "NSCOUNT",
        "arcount": "ARCOUNT",
    }

    dns_abuf_contents = [
        "opcode",
        "rcode",
        "nsid",
    ]

    column_names = list(outer_contents.keys())
    column_names.extend(result_contents.keys())
    column_names.extend(result_result_contents.keys())
    column_names.extend(dns_abuf_contents)

    with pyfsdb.Fsdb(
        out_file_handle=args.output_file, out_column_names=column_names
    ) as outh:
        for content in contents:

            # content is either a single response itself, or contains
            # some fields inside a "resultset".  We fake the resultset
            # here by just nesting the content within it, so all the code
            # below works either in the multiple case or a singular case
            if "resultset" not in content and "result" in content:
                content["resultset"] = [content]

            # TODO(hardaker): errors need handling here (no result, just 'error')
            if "resultset" not in content:
                continue
            for result in content["resultset"]:
                row = [content.get(outer_contents[key]) for key in outer_contents]
                row.extend([result.get(result_contents.get(key)) for key in result_contents])

                if "result" in result:
                    row.extend([result["result"].get(result_result_contents[key]) for key in result_result_contents])

                    if "abuf" in result["result"]:
                        try:
                            dnsmsg = dns.message.from_wire(base64.b64decode(result["result"]["abuf"]))

                            row.append(dnsmsg.opcode().name)
                            row.append(dnsmsg.rcode().name)

                            # get the NSID of the server's response
                            nsid_option = dnsmsg.get_options(dns.edns.NSID)
                            if nsid_option and len(nsid_option) > 0:
                                # TODO(hardaker): what is len > 1 mean?
                                text = nsid_option[0].to_text()
                                if text.startswith("NSID "):
                                    text = text[5:]
                                row.append(text)
                            else:
                                row.append(None)

                        except:
                            row.extend([None for x in dns_abuf_contents])

                        # TODO(hardaker): iterate over rrset...
                        # TODO(hardaker): iterate over extended_errors
                        # TODO(hardaker): iterate over options
                        # TODO(hardaker): many other dns.message.QueryMessage fields

                    else:
                        row.extend([None for x in dns_abuf_contents])

                else:
                    # fill missing data with Nones
                    row.extend([None for x in result_result_contents])
                    row.extend([None for x in dns_abuf_contents])

                outh.append(row)


if __name__ == "__main__":
    main()
