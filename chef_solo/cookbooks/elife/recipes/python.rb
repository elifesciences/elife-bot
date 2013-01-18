# eLife chef python pip packages
# v 0.1
# January 17, 2013
#

include_recipe "python::pip"

pip_packages = "requests==0.13.0","lxml","beautifulsoup4","fom","lettuce","boto"

# Uninstall requests version 1, because it is failing
python_pip "requests" do
	action :remove
end

pip_packages.each do |elife_pip_pack|
	python_pip elife_pip_pack do
		action :install
	end
end

