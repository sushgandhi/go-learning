// middleware/store.go

package middleware

import (
	"github.com/gin-gonic/gin"
	"github.com/yourusername/yourproject/store"
	"go.mongodb.org/mongo-driver/mongo"
)

func WithUserStore(collection *mongo.Collection) gin.HandlerFunc {
	return func(c *gin.Context) {
		userStore := &store.MongoUserStore{collection: collection}
		c.Set("userStore", userStore)
		c.Next()
	}
}

------------------
// store/userstore.go

package store

import (
    "context"

    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/mongo"
)

type UserStore interface {
    GetUserDetailsByID(ctx context.Context, userID string) (bson.M, error)
    AddUser(ctx context.Context, userDetail bson.M) (interface{}, error)
}

type MongoUserStore struct {
    collection *mongo.Collection
}

func (m *MongoUserStore) GetUserDetailsByID(ctx context.Context, userID string) (bson.M, error) {
    filter := bson.D{{"userid", userID}}
    var userDetail bson.M
    err := m.collection.FindOne(ctx, filter).Decode(&userDetail)
    return userDetail, err
}

func (m *MongoUserStore) AddUser(ctx context.Context, userDetail bson.M) (interface{}, error) {
    result, err := m.collection.InsertOne(ctx, userDetail)
    return result, err
}


// services/userdetails.go

package services

import (
    "context"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/yourusername/yourproject/store"
)

func GetUserDetailsByIDHandler(s store.UserStore) gin.HandlerFunc {
    // ...
}

func AddUserHandler(s store.UserStore) gin.HandlerFunc {
    // ...
}


// main.go

func main() {
    // ...

    userCollection := client.Database("yourdatabase").Collection("userdetail")
    userStore := &store.MongoUserStore{collection: userCollection}

    router.GET("/userdetails/:id", services.GetUserDetailsByIDHandler(userStore))
    router.POST("/userdetails", services.AddUserHandler(userStore))

    // ...
}
