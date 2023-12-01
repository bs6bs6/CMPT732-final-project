import sys

assert sys.version_info >= (3, 5)  # make sure we have Python 3.5+
from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StringIndexer, OneHotEncoder
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
from pyspark.sql import types, functions


# add more functions as necessary
schema = types.StructType(
    [
        types.StructField("timestamp", types.TimestampType()),
        types.StructField("dayofweek", types.IntegerType()),
        types.StructField("hour", types.IntegerType()),
        types.StructField("state", types.StringType()),
        types.StructField("candidate", types.StringType()),
        types.StructField("likes", types.StringType()),
        types.StructField("retweet_count", types.StringType()),
        types.StructField("online_age", types.FloatType()),
        types.StructField("user_followers_count", types.StringType()),
        types.StructField("lat", types.FloatType()),
        types.StructField("long", types.FloatType()),
        types.StructField("tweet", types.StringType()),
        types.StructField("sentiment", types.StringType()),
        types.StructField("language", types.StringType()),
    ]
)


def main(inputs, model_file):
    data = spark.read.csv(inputs, schema=schema)

    train, validation = data.randomSplit([0.75, 0.25])
    train = train.cache()
    validation = validation.cache()
    # OneHotEncoder for multi-class categorical column (language)
    language_encoder = OneHotEncoder(
        inputCol="language_indexed", outputCol="language_encoded"
    )

    feature_cols = [
        "hour",
        "dayofweek",
        "online_age",
        "candidate_indexed",
        "language_encoded",
    ]

    # Modify StringIndexer to handle unseen labels
    candidate_indexer = StringIndexer(
        inputCol="candidate", outputCol="candidate_indexed", handleInvalid="keep"
    )
    language_indexer = StringIndexer(
        inputCol="language", outputCol="language_indexed", handleInvalid="keep"
    )
    sentiment_indexer = StringIndexer(
        inputCol="sentiment", outputCol="sentiment_indexed", handleInvalid="keep"
    )

    # Ensure the column data types are correct
    data = data.withColumn("candidate", functions.col("candidate").cast("string"))
    data = data.withColumn("language", functions.col("language").cast("string"))
    data = data.withColumn("sentiment", functions.col("sentiment").cast("string"))

    # VectorAssembler to create feature vector
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")

    # Define the classification model
    classifier = RandomForestClassifier(
        featuresCol="features", labelCol="sentiment_indexed"
    )

    # Define the pipeline
    pipeline = Pipeline(
        stages=[
            sentiment_indexer,
            candidate_indexer,
            language_indexer,
            language_encoder,
            assembler,
            classifier,
        ]
    )

    # Fit the model
    model = pipeline.fit(train)
    # Evaluate the model
    evaluator = MulticlassClassificationEvaluator(
        labelCol="sentiment_indexed", predictionCol="prediction", metricName="accuracy"
    )
    train_data = model.transform(train)
    validation_data = model.transform(validation)

    accuracy_train = evaluator.evaluate(train_data)
    accuracy_validation = evaluator.evaluate(validation_data)
    print(f"Accuracy on train data = {accuracy_train}")
    print(f"Accuracy on validation data = {accuracy_validation}")

    # Save the model
    model.write().overwrite().save(model_file)


if __name__ == "__main__":
    inputs = sys.argv[1]
    model_file = sys.argv[2]
    spark = SparkSession.builder.appName("wearher train").getOrCreate()
    assert spark.version >= "3.0"  # make sure we have Spark 3.0+
    spark.sparkContext.setLogLevel("WARN")
    sc = spark.sparkContext
    main(inputs, model_file)
