def process_rasters(input_paths: List[str], multipliers: List[float], output_path: str) -> str:
    if len(input_paths) != len(multipliers):
        print("❌ Error: Listas de archivos y multiplicadores deben tener la misma longitud.")
        return ""

    aligned_paths = check_and_align_rasters(input_paths)
    if not aligned_paths:
        print("❌ Error: No se generaron archivos alineados.")
        return ""

    base_dataset = gdal.Open(aligned_paths[0])
    if not base_dataset:
        print("❌ Error: No se pudo abrir la capa base.")
        return ""

    base_crs = base_dataset.GetProjection()
    base_transform = base_dataset.GetGeoTransform()
    base_width = base_dataset.RasterXSize
    base_height = base_dataset.RasterYSize

    driver = gdal.GetDriverByName('GTiff')
    output_directory = os.path.dirname(output_path)
    os.makedirs(output_directory, exist_ok=True)

    output_dataset = driver.Create(output_path, base_width, base_height, 1, gdal.GDT_Float32)
    if output_dataset is None:
        print("❌ Error: No se pudo crear el archivo de salida.")
        return ""

    output_dataset.SetGeoTransform(base_transform)
    output_dataset.SetProjection(base_crs)
    out_band = output_dataset.GetRasterBand(1)
    out_band.SetNoDataValue(255.0)

    for y in range(0, base_height, BLOCK_SIZE):
        block_height = min(BLOCK_SIZE, base_height - y)

        for x in range(0, base_width, BLOCK_SIZE):
            block_width = min(BLOCK_SIZE, base_width - x)

            sum_block = np.zeros((block_height, block_width), dtype=np.float32)
            valid_mask_global = np.zeros_like(sum_block, dtype=bool)

            for i, input_path in enumerate(aligned_paths):
                multiplier = multipliers[i]
                dataset = gdal.Open(input_path)
                if not dataset:
                    print(f"❌ Error al abrir {input_path}.")
                    continue

                band = dataset.GetRasterBand(1)
                nodata = band.GetNoDataValue()
                if nodata is None:
                    nodata = 255.0

                array = band.ReadAsArray(x, y, block_width, block_height)
                if array is None:
                    continue

                array = array.astype(np.float32)
                valid_mask = (array != nodata) & (~np.isnan(array)) & (~np.isinf(array))
                processed = np.where(valid_mask, array * multiplier, 0)

                sum_block += processed
                valid_mask_global |= valid_mask

            # Donde no hubo ningún valor válido, marcar como NoData
            sum_block[~valid_mask_global] = 255.0

            # Forzar tope para evitar que valores válidos igualen o superen NoData
            sum_block = np.where(sum_block >= 255.0, 254.999, sum_block)

            print(f"🧩 Block ({x},{y}) stats: min={np.nanmin(sum_block)}, max={np.nanmax(sum_block)}, unique={np.unique(sum_block)}")
            out_band.WriteArray(sum_block, x, y)

    out_band.ComputeStatistics(False)
    out_band, output_dataset = None, None

    print(f"✅ Raster generado en: {output_path}")
    return output_path
