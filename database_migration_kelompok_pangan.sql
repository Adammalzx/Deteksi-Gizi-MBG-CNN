-- Jalankan sekali pada database mbg_db jika tabel tkpi belum memiliki kolom klasifikasi pangan.
ALTER TABLE tkpi
    ADD COLUMN kelompok_pangan VARCHAR(50) NULL AFTER nama_makanan,
    ADD COLUMN keterangan_gizi VARCHAR(255) NULL AFTER kelompok_pangan;

UPDATE tkpi
SET kelompok_pangan = CASE LOWER(nama_makanan)
    WHEN 'nasi' THEN 'Karbohidrat'
    WHEN 'kentang' THEN 'Karbohidrat'
    WHEN 'mie' THEN 'Karbohidrat'
    WHEN 'roti' THEN 'Karbohidrat'
    WHEN 'ayam' THEN 'Protein hewani'
    WHEN 'bakso' THEN 'Protein hewani'
    WHEN 'telur' THEN 'Protein hewani'
    WHEN 'tempe' THEN 'Protein nabati'
    WHEN 'tahu' THEN 'Protein nabati'
    WHEN 'kacang' THEN 'Protein nabati'
    WHEN 'sayur' THEN 'Serat & vitamin'
    WHEN 'buah' THEN 'Serat & vitamin'
    WHEN 'susu' THEN 'Kalsium & protein'
    WHEN 'keju' THEN 'Lemak & kalsium'
    ELSE 'Lainnya'
END,
keterangan_gizi = CASE LOWER(nama_makanan)
    WHEN 'nasi' THEN 'Sumber energi utama dari karbohidrat.'
    WHEN 'kentang' THEN 'Sumber karbohidrat dan kalium.'
    WHEN 'mie' THEN 'Sumber karbohidrat untuk energi.'
    WHEN 'roti' THEN 'Sumber karbohidrat praktis.'
    WHEN 'ayam' THEN 'Sumber protein hewani untuk pertumbuhan.'
    WHEN 'bakso' THEN 'Sumber protein hewani.'
    WHEN 'telur' THEN 'Sumber protein hewani dan zat gizi mikro.'
    WHEN 'tempe' THEN 'Sumber protein nabati dan serat.'
    WHEN 'tahu' THEN 'Sumber protein nabati.'
    WHEN 'kacang' THEN 'Sumber protein nabati dan lemak baik.'
    WHEN 'sayur' THEN 'Sumber serat, vitamin, dan mineral.'
    WHEN 'buah' THEN 'Sumber vitamin, mineral, dan serat.'
    WHEN 'susu' THEN 'Sumber kalsium dan protein.'
    WHEN 'keju' THEN 'Sumber kalsium dan lemak.'
    ELSE 'Kelompok pangan belum diklasifikasikan.'
END;
