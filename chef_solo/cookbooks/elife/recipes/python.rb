# eLife chef python pip packages
# v 0.1
# January 17, 2013
#

include_recipe "python::pip"

pip_packages = "lxml","beautifulsoup4","fom","lettuce","boto"

pip_packages.each do |elife_pip_pack|
	python_pip elife_pip_pack do
		action :install
	end
end