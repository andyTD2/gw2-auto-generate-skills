Script to generate basic representations of profession skills using gw2wingman and arcdps_log_tools.

requirements:
	-python 3.8+
	-Zerthox's arcdps_log_tools (https://github.com/Zerthox/arcdps-log-tools)
usage:
	REQIORED: wingman profSkill json files
		- A set of files are already included; skip this step unless you want more up-to-date skill data
		- Place inside "profession_data"
		- Data can be found https://gw2wingman.nevermindcreations.de/api/profSkills/Dragonhunter, must adhere to same format
		- Will use to files to generate some skill data(damage coefficients, cast times, condis applied, etc.)

	OPTIONAL: arcdps .zvetc files
		- Place into a folder named "arc_log_files" inside the root directory or provide a path to folder containing them
		- Will use these files to run arc_dps_log_tools.exe to generate tick data
		- Failure to provide these files will result in missing tick data
		- If you already have tick data from arc_dps_log_tools.exe, you can place them in tick_data

	
	USAGE:	python generate_skills.py <PATH TO ARCDPS_LOG_TOOLS.EXE> <PATH TO FOLDER CONTAINING .zevtc LOGS>
		<PATH TO ARCDPS_LOG_TOOLS.EXE>: REQUIRED
		<PATH TO FOLDER CONTAINING .zevtc LOGS>: OPTIONAL, will use arcdps_log_files folder by default

	OUTPUT:	results placed in output folder

