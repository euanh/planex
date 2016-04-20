#!/usr/bin/env python

import argparse
import json
import os
import sys
import urlparse
from datetime import datetime

from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler
import planex.spec

import requests

import argcomplete


def parse_args_or_exit(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files")
    add_common_parser_options(parser)
    parser.add_argument("spec", help="RPM spec file")
    parser.add_argument('--no-package-name-check', dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def all_sources(spec, topdir, check_package_names):
    """
    Get all sources defined in the spec file
    """
    spec = planex.spec.Spec(spec, topdir=topdir,
                            check_package_name=check_package_names)
    urls = [urlparse.urlparse(url) for url in spec.source_urls()]
    return zip(spec.source_paths(), urls)


def get_all(uri, headers):
    res = requests.get(uri, headers=headers)
    responses = res.json()
    while 'next' in res.links:
        res = requests.get(res.links['next']['url'], headers=headers)
        responses.extend(res.json())
    return responses

def get_tag(headers, owner, repo, sha):
    fetchurl = "https://api.github.com/repos/%s/%s/git/tags/%s" % (owner, repo, sha)
    return requests.get(fetchurl, headers=headers)

def get_commit(headers, owner, repo, sha):
    fetchurl = "https://api.github.com/repos/%s/%s/git/tags/%s" % (owner, repo, sha)
    return requests.get(fetchurl, headers=headers)


def parse_iso8601_timestamp(timestamp):
    return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")


def get_commit_date(url, headers):
    res = requests.get(url, headers=headers)
    return parse_iso8601_timestamp(res.json()['commit']['committer']['date'])


def get_tags(headers, owner, repo):
    fetchurl = "https://api.github.com/repos/%s/%s/tags" % (owner, repo)
    res = get_all(fetchurl, headers)
    
    dated = [(t['name'], get_commit_date(t['commit']['url'], headers=headers)) for t in res]
    dated.sort(key=lambda x: x[1], reverse=True)
    return dated
    
    
def main(argv):
    args = parse_args_or_exit(argv)

    headers = {}
    if 'GH_TOKEN' in os.environ:
        headers['Authorization'] = "token %s" % os.environ['GH_TOKEN']

    spec = planex.spec.Spec(args.spec, topdir="badger",
                            check_package_name=args.check_package_names)
    sources = all_sources(args.spec, "badger", args.check_package_names)
    for path, url in sources:
       if "github.com" in url.netloc:
            # Every GitHub release corresponds to a tag
            # Not every tag corresponds to a release
            # Some projects add tags but don't create releases
            # Tags are not reported by the releases query
            #   -> a project may have tagged a 'release' later than the latest
            #      GitHub release, but this won't show up in the releases list
            # This script is just a helper and doesn't need to be perfect.
            # It is better to give a false positive (which will be found out
            # by the user through testing) than a false negative (to hide a 
            # genuine release)

            owner, repo = url.path.split(os.sep)[1:3]
            fetchurl = "https://api.github.com/repos/%s/%s/releases/latest" % (owner, repo)
            latest_release = requests.get(fetchurl, headers=headers)
            

            # Check the tags first.  Every release must have a tag,
            # but a tag does not necessarily correspond to a release.

            tags = get_tags(headers, owner, repo)
	    if not tags:
		print "%s: could not find any releases or tags" % spec.name()
		sys.exit(1)

            # new strategy - first check the latest release, then get the list of tags and look for things which look like versions (contain a semantic version tuple) and sort by that

            import re
            def key_of_tag(tag):
                match = re.search("(\d+(\.\d+)+)", tag)
                if match:
                    return match.group(1)
                else:
                    return None

            # filter out nones, then use distutils.version.StrictVersion to compare them
j

	    latest_tag = tags[0][0]

            # https://api.github.com/repos/:owner/:repo/releases/latest returns the latest
            # release, but ignores pre-releases and drafts.   Many of our packages are 
            # pre-releases.
            # releases does not include tags which are not associated to GitHub releases
            fetchurl = "https://api.github.com/repos/%s/%s/releases" % (owner, repo)
            res = requests.get(fetchurl, headers=headers)
            if not res.ok:
                print "%s: something went wrong" % spec.name()
                sys.exit(1)
                 
            if res.ok and res.json():
                latest_release_tag = res.json()[0]['tag_name']

    	    if latest_tag.endswith(spec.version()):
                print "%s: current version %s is the latest release" % (spec.name(), spec.version())
    	    else:
                print "%s: current version %s; a newer release (%s) is available" % (spec.name(), spec.version(), latest_tag)
                sys.exit(1)
            
           

def _main():
    main(sys.argv[1:])

if __name__ == "__main__":
    _main()
