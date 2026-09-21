@echo off
rem Toolchain smoke test - verifies the Phase 3 build chain end to end:
rem   vcvars64 (x64 MSVC) -> cl.exe compiles+runs C -> nvcc compiles CUDA for sm_120
rem Verified working 2026-09-21. Self-contained: generates its own test sources.
rem NOTE: the explicit CUDA PATH line matters in shells started BEFORE the CUDA
rem install; fresh shells pick it up from the machine PATH automatically.
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 1
set PATH=%PATH%;C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.4\bin
echo #include ^<stdio.h^> > hello.c
echo int main(void) { printf("hello from cl\n"); return 0; } >> hello.c
echo __global__ void k(){} > trivial.cu
echo int main(void) { return 0; } >> trivial.cu
echo VCVARS_OK
cl /nologo hello.c || exit /b 2
hello.exe || exit /b 3
nvcc -c -arch=sm_120 trivial.cu -o trivial.obj || exit /b 4
echo NVCC_SMOKE_OK
