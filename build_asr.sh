git clone https://github.com/k2-fsa/sherpa-onnx.git
cd sherpa-onnx
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DSHERPA_ONNX_ENABLE_GPU=ON ..
make -j6
pip install .