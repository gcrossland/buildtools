@ECHO OFF
REM PATH=I:\Apps\PROGRA~1\MINGW4~1.8\bin;%PATH%

set CMD_RM=I:\Apps\Platforms\Cygwin\bin\rm.exe -rf
set CMD_MKDIR=I:\Apps\Platforms\Cygwin\bin\mkdir.exe --parents
set CMD_CP=I:\Apps\Platforms\Cygwin\bin\cp.exe
set PLATFORM=WIN32_IA_32
set LIBCACHEDIR=../../cache
set CONFIG=debug
set FLAGS=-std=gnu++11 -Wl,--demangle -O0 -gstabs3 -fno-omit-frame-pointer -Wconversion -Wctor-dtor-privacy -Wnon-virtual-dtor -Wreorder -Wold-style-cast -Woverloaded-virtual -Wchar-subscripts -Wformat -Wmissing-braces -Wparentheses -Wsequence-point -Wreturn-type -Wunused-variable -Wstrict-aliasing -Wstrict-overflow -Wextra -Wfloat-equal -Wpointer-arith -Waddress -Wmissing-field-initializers -Winline -Winvalid-pch -Wdisabled-optimization -Wno-non-template-friend
REM vs -std=c++11
REM -Wp,-std=c99
REM -Wno-type-limits
REM consider -Wall -Wextra
set DLLS=I:/Apps/PROGRA~1/MINGW4~1.8/bin/libgcc_s_dw2-1.dll I:/Apps/PROGRA~1/MINGW4~1.8/bin/libstdc++-6.dll I:/Apps/PROGRA~1/MINGW4~1.8/bin/libwinpthread-1.dll