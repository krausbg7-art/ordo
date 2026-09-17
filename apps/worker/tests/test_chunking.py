from ordo_worker.chunking import split_into_chunks


def test_empty_text_produces_no_chunks():
    assert split_into_chunks("") == []
    assert split_into_chunks("   ") == []


def test_short_text_is_a_single_chunk():
    chunks = split_into_chunks("короткий текст", size=1500, overlap=200)
    assert chunks == ["короткий текст"]


def test_long_text_is_split_with_overlap():
    text = "a" * 4000
    chunks = split_into_chunks(text, size=1500, overlap=200)

    assert len(chunks) > 1
    assert all(len(c) <= 1500 for c in chunks)
    # конец одного фрагмента пересекается с началом следующего
    assert chunks[0][-100:] in text
    assert "".join(dict.fromkeys(chunks[0] + chunks[1]))  # оба фрагмента непустые
