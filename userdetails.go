// store/mongodb.go

package store

import (
    "context"

    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/mongo"
    "go.mongodb.org/mongo-driver/mongo/options"
)

type MongoDB interface {
    FindOne(ctx context.Context, filter bson.D) (bson.M, error)
    Find(ctx context.Context, filter bson.D) ([]bson.M, error)
    InsertOne(ctx context.Context, document bson.M) (interface{}, error)
    UpdateOne(ctx context.Context, filter bson.D, update bson.D) (*mongo.UpdateResult, error)
    DeleteOne(ctx context.Context, filter bson.D) (*mongo.DeleteResult, error)
}

type MongoDBStore struct {
    collection *mongo.Collection
}

func (m *MongoDBStore) FindOne(ctx context.Context, filter bson.D) (bson.M, error) {
    var result bson.M
    err := m.collection.FindOne(ctx, filter).Decode(&result)
    return result, err
}

func (m *MongoDBStore) Find(ctx context.Context, filter bson.D) ([]bson.M, error) {
    cursor, err := m.collection.Find(ctx, filter)
    if err != nil {
        return nil, err
    }
    var results []bson.M
    if err = cursor.All(ctx, &results); err != nil {
        return nil, err
    }
    return results, nil
}

func (m *MongoDBStore) InsertOne(ctx context.Context, document bson.M) (interface{}, error) {
    result, err := m.collection.InsertOne(ctx, document)
    return result, err
}

func (m *MongoDBStore) UpdateOne(ctx context.Context, filter bson.D, update bson.D) (*mongo.UpdateResult, error) {
    result, err := m.collection.UpdateOne(ctx, filter, update)
    return result, err
}

func (m *MongoDBStore) DeleteOne(ctx context.Context, filter bson.D) (*mongo.DeleteResult, error) {
    result, err := m.collection.DeleteOne(ctx, filter)
    return result, err
}

// services/userdetails.go

func GetUserDetailsByIDHandler(c *gin.Context) {
	userID := c.Param("id")
	userStore := c.MustGet("userStore").(store.UserStore)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Second)
	defer cancel()

	userDetail, err := userStore.GetUserDetailsByID(ctx, userID)
	if err != nil {
		// handle error
	}

	c.JSON(http.StatusOK, userDetail)
}

func AddUserHandler(c *gin.Context) {
	userDetail := c.MustGet("userDetail").(bson.M)
	userStore := c.MustGet("userStore").(store.UserStore)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Second)
	defer cancel()

	result, err := userStore.AddUser(ctx, userDetail)
	if err != nil {
		// handle error
	}

	c.JSON(http.StatusOK, result)
}
