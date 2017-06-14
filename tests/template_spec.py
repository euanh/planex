"""Template spec file for testing"""

from jinja2 import Template

TEMPLATE = Template("""
Name:           {{name}}
Version:        {{version}}
Release:        {{release}}%{?dist}
Summary:        Test package
License:        GPLv2
URL:            https://www.citrix.com/
{%- for source in sources %}
Source{{loop.index0}}:        {{source}}
{%- endfor %}
{%- for patch in patches %}
Patch{{loop.index0}}:         {{patch}}
{%- endfor %}
{%- for req in buildrequires %}
BuildRequires:  {{req}}
{%- endfor %}
{%- for prov in provides %}
Provides:       {{prov}}
{%- endfor %}

%description
Dummy {{name}} package

%prep
%autosetup -p1

%build
# This section intentionally left blank

%install
# This section intentionally left blank

%files
# This section intentionally left blank

%changelog
* Fri Jun 9 2017 Testy McTestface <testy@example.com> - {{version}}-{{release}}
- Added things to package
""")


def render(params):
    """Return a template spec file suitable for testing"""
    return TEMPLATE.render(name=params.get("name", "dummy"),
                           version=params.get("version", "1.2.3"),
                           release=params.get("release", "1"),
                           buildrequires=params.get("buildrequires", []),
                           requires=params.get("requires", []),
                           provides=params.get("provides", []),
                           sources=params.get("sources", []),
                           patches=params.get("patches", []))
