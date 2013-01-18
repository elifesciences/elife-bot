# eLife chef OS packages
# v 0.1
# January 17, 2013
#

include_recipe "build-essential"

packages = "libxml2","libxslt-dev"

packages.each do |elife_pack|
  package elife_pack do
		action :nothing
	end.run_action(:install)
end