import pytest
from multi_asset.ai_brief import validate
from multi_asset.database import merge_sql

def response(value=24):
    return {"claims":[{"metric_key":"n","value":value,"explanation":"Number of observations."}]}

def test_ai_exact_typed_facts():assert validate(response(),{"n":24})

@pytest.mark.parametrize("value",["24",24.0,True,25])
def test_ai_rejects_changed_type_or_value(value):
    with pytest.raises(ValueError):validate(response(value),{"n":24})

def test_ai_rejects_missing_claim():
    with pytest.raises(ValueError):validate({"claims":[]},{"n":24})

def test_ai_rejects_duplicates():
    r=response();r["claims"]*=2
    with pytest.raises(ValueError):validate(r,{"n":24})

def test_ai_rejects_unknown_key():
    with pytest.raises(ValueError):validate(response(),{"count":24})

def test_merge_is_locked_and_upsert_only():
    sql=merge_sql("assets","stage_012345abcdef",["ticker","name"],["ticker"])
    assert "HOLDLOCK" in sql and "WHEN MATCHED" in sql and "WHEN NOT MATCHED" in sql
    assert "DELETE" not in sql and "TRUNCATE" not in sql

@pytest.mark.parametrize("table,stage,columns",[("evil","stage_012345abcdef",["ticker","name"]),("assets","x; DROP TABLE a",["ticker","name"]),("assets","stage_012345abcdef",["ticker","bad]column"])])
def test_sql_identifier_validation(table,stage,columns):
    with pytest.raises(ValueError):merge_sql(table,stage,columns,["ticker"])
