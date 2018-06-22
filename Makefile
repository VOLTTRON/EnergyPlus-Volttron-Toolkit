base_dir := /home/vuser/volttron/simulations
target_dir := $(shell date +%Y%m%d_%H%M%S)

b1_ilc_dir := $(base_dir)/building1_ilc
b1_ilc_target_dir := $(b1_ilc_dir)/$(target_dir)

b1_tcc_fd_dir := $(base_dir)/building1_tcc_fd
b1_tcc_fd_target_dir := $(b1_tcc_fd_dir)/$(target_dir)

b1_tcc_fp_dir := $(base_dir)/building1_tcc_fp
b1_tcc_fp_target_dir := $(b1_tcc_fp_dir)/$(target_dir)


so_ilc_dir := $(base_dir)/small_office_ilc
so_tcc_dir := $(base_dir)/small_office_tcc

so_ilc_target_dir := $(so_ilc_dir)/$(target_dir)
so_tcc_target_dir := $(so_tcc_dir)/$(target_dir)

pre:
	@echo "Removing old files..."
	rm -f eplus/eplusout.sql
	rm -f eplus/baseline_eplusout.sql
	rm -f eplus/eplusout.csv
	@echo "Starting volttron..."
	rm -f /home/vuser/.volttron/auth.json
	./start-volttron
	sleep 10

run_base_so: pre
	@echo "Running baseline..."
	python run.py s1
	counter=1; while ! [ -f eplus/baseline_eplusout.sql ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done 
	rm -f eplus/eplusout.csv

run_base_building1: pre
	@echo "Running baseline..."
	python run.py b1
	counter=1; while ! [ -f eplus/eplusout.csv ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done 
	rm -f eplus/eplusout.csv

b1_ilc: run_base_building1
	mkdir -p $(b1_ilc_target_dir)
	cp eplus/baseline_eplusout.sql $(b1_ilc_target_dir)
	. upgrade-scripts/upgrade-b1-ilc
	counter=1; while ! [ -f eplus/eplusout.csv ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done 
	@echo "Writing result to disk..."
	sleep 10
	cp eplus/BUILDING1.idf $(b1_ilc_target_dir)
	cp -r config/ilc/building1/. $(b1_ilc_target_dir)
	cp eplus/eplusout.sql $(b1_ilc_target_dir)
	cp eplus/eplusout.csv $(b1_ilc_target_dir)
	mv volttron.log $(b1_ilc_target_dir)
	@echo "You can view result at http://localhost"
	@echo "Cleaning up..."
	. env/bin/activate && vctl shutdown --platform -t 100 2>/dev/null; true

b1_tcc_fd: run_base_building1
	mkdir -p $(b1_tcc_fd_target_dir)
	cp eplus/baseline_eplusout.sql $(b1_tcc_fd_target_dir)
	. upgrade-scripts/upgrade-b1-tcc-fixed-demand
	counter=1; while ! [ -f eplus/eplusout.csv ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done 
	@echo "Writing result to disk..."
	sleep 10
	cp eplus/BUILDING1.idf $(b1_tcc_fd_target_dir)
	cp -r config/tcc/building1/. $(b1_tcc_fd_target_dir)
	cp eplus/eplusout.sql $(b1_tcc_fd_target_dir)
	cp eplus/eplusout.csv $(b1_tcc_fd_target_dir)
	cp eplus/tccpower.csv $(b1_tcc_fd_target_dir)
	cp eplus/tccpower_baseline.csv $(b1_tcc_fd_target_dir)
	mv volttron.log $(b1_tcc_fd_target_dir)
	@echo "You can view result at http://localhost"
	@echo "Cleaning up..."
	. env/bin/activate && vctl shutdown --platform -t 100 2>/dev/null; true

b1_tcc_fp: run_base_building1
	mkdir -p $(b1_tcc_fp_target_dir)
	cp eplus/baseline_eplusout.sql $(b1_tcc_fp_target_dir)
	. upgrade-scripts/upgrade-b1-tcc-fixed-price
	counter=1; while ! [ -f eplus/eplusout.csv ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done 
	@echo "Writing result to disk..."
	sleep 10
	cp eplus/BUILDING1.idf $(b1_tcc_fp_target_dir)
	cp -r config/tcc/building1/. $(b1_tcc_fp_target_dir)
	cp eplus/eplusout.sql $(b1_tcc_fp_target_dir)
	cp eplus/eplusout.csv $(b1_tcc_fp_target_dir)
	cp eplus/tccpower.csv $(b1_tcc_fp_target_dir)
	cp eplus/tccpower_baseline.csv $(b1_tcc_fp_target_dir)
	mv volttron.log $(b1_tcc_fp_target_dir)
	@echo "You can view result at http://localhost"
	@echo "Cleaning up..."
	. env/bin/activate && vctl shutdown --platform -t 100 2>/dev/null; true

so_ilc: run_base_so
	mkdir -p $(so_ilc_target_dir)
	cp eplus/baseline_eplusout.sql $(so_ilc_target_dir)
	. upgrade-scripts/upgrade-so-ilc
	counter=1; while ! [ -f eplus/eplusout.csv ]; do counter=`expr $$counter + 1`; echo "Simulation is in progress... Do not close this terminal or start another simulation. Time elapsed: $$counter second."; sleep 1; done
	@echo "Writing result to disk..."
	sleep 10
	cp eplus/Small_Office.idf $(so_ilc_target_dir)
	cp -r config/ilc/small_office/. $(so_ilc_target_dir)
	cp eplus/eplusout.sql $(so_ilc_target_dir)
	cp eplus/eplusout.csv $(so_ilc_target_dir)
	mv volttron.log $(so_ilc_target_dir)
	@echo "You can view result at http://localhost"
	@echo "Cleaning up..."
	. env/bin/activate && vctl shutdown --platform -t 100 2>/dev/null; true

clean_sm_ilc:
	rm -rf $(so_ilc_dir)

clean_b1_ilc:
	rm -rf $(b1_ilc_dir)

clean_b1_tcc_fd:
	rm -rf $(b1_tcc_fd_dir)

clean_b1_tcc_fp:
	rm -rf $(b1_tcc_fp_dir)

clean_all: clean_sm_ilc clean_b1_ilc clean_b1_tcc_fd clean_b1_tcc_fp
	@echo "Clean all completed."

update:
	git pull
	sudo service nginx restart
	sudo systemctl restart dashboard.service

shutdown:
	. env/bin/activate && vctl shutdown --platform -t 100 2>/dev/null; true
