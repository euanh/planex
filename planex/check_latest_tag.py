#!/usr/bin/env python

import argparse
import json
import os
import sys
import urlparse
import fileinput
from datetime import datetime

from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler
import planex.spec

import requests

import argcomplete
import re
import distutils.version
import subprocess


def parse_args_or_exit(argv=None):
    parser = argparse.ArgumentParser(
        description="Check that the latest tag on a repository referenced by a spec file points to head")
    add_common_parser_options(parser)
    parser.add_argument("spec", help="RPM spec file")
    parser.add_argument('--no-package-name-check', dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    parser.add_argument('--update',
                        action="store_true", default=False,
                        help="Update spec file to use latest release file name")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def all_sources(spec):
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
    return get_all(fetchurl, headers)
    
def main(argv):
    args = parse_args_or_exit(argv)

    headers = {}
    if 'GH_TOKEN' in os.environ:
        headers['Authorization'] = "token %s" % os.environ['GH_TOKEN']

    spec = planex.spec.Spec(args.spec, topdir="badger", check_package_name=args.check_package_names)
    sources = all_sources(spec)

    git_name = subprocess.check_output(["git", "config", "user.name"]).strip()
    git_email = subprocess.check_output(["git", "config", "user.email"]).strip()

    for _, url in sources:
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
            latest_tag = None

            # Check the tags first.  Every release must have a tag,
            # but a tag does not necessarily correspond to a release.

            tags = get_tags(headers, owner, repo)
	    if not tags:
		print "%s: repo has no tags" % spec.name()
		sys.exit(1)

            def key_of_tag(tag):
                match = re.search(r"(\d+(\.\d+)+)", tag['name'])
                if match:
                    return distutils.version.LooseVersion(match.group(1))
                else:
                    return distutils.version.LooseVersion("0")


            tags.sort(key=key_of_tag, reverse=True)
            latest_tag = tags[0]

            repo_url = "https://api.github.com/repos/%s/%s/tags" % (owner, repo)
    	    if spec.version() in latest_tag['name']:
                print "%s: current version %s is the latest tag (%s, %s)" % (spec.name(), spec.version(), repo_url, latest_tag['name'])
    	    else:
                print "%s: current version %s; a newer release (%s, %s) is available" % (spec.name(), spec.version(), repo_url, latest_tag['name'])
		if not args.update:
                    sys.exit(1)

	        for line in fileinput.input(args.spec, inplace=True):
                    match = re.match(r'^([Vv]ersion:\s+)(.+)', line)
                    if match:
                        print "%s%s" % (match.group(1), key_of_tag(latest_tag))
                        continue

                    match = re.match(r'^([Rr]elease:\s+)\d+(.+)', line)
                    if match:
                        print "%s%s%s" % (match.group(1), "1", match.group(2))
                        continue

                    match = re.match(r'^%changelog', line)
                    if match:
                        print line,
                        timestamp = datetime.now().strftime("%a %b %d %Y")
                        print "* %s %s <%s> - %s-1" % (timestamp, git_name, git_email, key_of_tag(latest_tag))
                        print "- Update to %s" % key_of_tag(latest_tag)
                        print ""

                        continue
             
                    print line,


           

def _main():
    main(sys.argv[1:])

if __name__ == "__main__":
    _main()
